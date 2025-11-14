from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from langchain_community.vectorstores import FAISS
try:
    from openai import OpenAI  # new SDK
    _OPENAI_SDK = "new"
except Exception:  # pragma: no cover
    OpenAI = None
    _OPENAI_SDK = "legacy"
    import openai as openai_legacy
from langchain_core.documents import Document

class VectorStoreNode:
    class Config(BaseModel):
        # Provider kept for UI compatibility; backend always uses OpenAI
        provider: str = "openai"
        name: str = "Vector Store"
        
    def __init__(self, config: Config, api_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.type = "vector_store"
        self.name = config.name
        self.inputs = ["documents", "embeddings"]
        self.outputs = ["vector_store", "retriever"]
        self.config = config
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        # Use a lightweight embeddings wrapper using the OpenAI client directly
        self.model = "text-embedding-ada-002"
        self.api_key = api_key
        # Lazy initialize embeddings object in process() to avoid constructor-time SDK issues
        self.embeddings = None
        self.vector_store = None
        
    def process(self, documents: List[Document]) -> Dict[str, Any]:
        try:
            # Lazy initialize embeddings wrapper
            if self.embeddings is None:
                if _OPENAI_SDK == "new":
                    # Initialize client with minimal config to avoid proxy/environment issues
                    import os
                    import httpx
                    # Create httpx client without proxies to avoid version conflicts
                    # Don't pass proxies parameter - let httpx default to no proxies
                    http_client = httpx.Client(timeout=60.0)
                    client_kwargs = {
                        "api_key": self.api_key,
                        "http_client": http_client
                    }
                    if os.getenv("OPENAI_TIMEOUT"):
                        try:
                            timeout_val = float(os.getenv("OPENAI_TIMEOUT"))
                            http_client = httpx.Client(timeout=timeout_val)
                            client_kwargs["http_client"] = http_client
                        except (ValueError, TypeError):
                            pass
                    client = OpenAI(**client_kwargs)
                    def _embed_docs(texts):
                        vectors = []
                        batch = 64
                        for i in range(0, len(texts), batch):
                            chunk = texts[i:i+batch]
                            resp = client.embeddings.create(model=self.model, input=chunk)
                            vectors.extend([d.embedding for d in resp.data])
                        return vectors
                    def _embed_query(text):
                        resp = client.embeddings.create(model=self.model, input=text)
                        return resp.data[0].embedding
                else:
                    openai_legacy.api_key = self.api_key
                    def _embed_docs(texts):
                        vectors = []
                        batch = 64
                        for i in range(0, len(texts), batch):
                            chunk = texts[i:i+batch]
                            resp = openai_legacy.Embedding.create(model=self.model, input=chunk)
                            vectors.extend([d["embedding"] for d in resp["data"]])
                        return vectors
                    def _embed_query(text):
                        resp = openai_legacy.Embedding.create(model=self.model, input=text)
                        return resp["data"][0]["embedding"]
                class _Emb:
                    def __init__(self, eq, ed):
                        self._eq, self._ed = eq, ed
                    def embed_query(self, t):
                        return self._eq(t)
                    def embed_documents(self, ts):
                        return self._ed(ts)
                    # Some vector stores expect a callable embedding function
                    # that behaves like embed_documents(texts).
                    def __call__(self, ts):
                        # FAISS still calls the embedding function directly for queries.
                        # When it does, it passes a single string (the query text).
                        # Our document embedding helper `_ed` expects an iterable of
                        # strings, so delegating to it would chunk the query by
                        # characters and return multiple embeddings, breaking FAISS
                        # (it expects a single vector and raises "too many values to
                        # unpack" when given a higher dimensional array).
                        if isinstance(ts, bytes):
                            ts = ts.decode("utf-8", errors="ignore")
                        if isinstance(ts, str):
                            return self._eq(ts)
                        if isinstance(ts, dict):
                            payload = (
                                ts.get("documents")
                                or ts.get("texts")
                                or ts.get("input")
                                or ts.get("data")
                            )
                            if payload is not None:
                                if not isinstance(payload, (list, tuple)):
                                    payload = [payload]
                                normalized = [
                                    getattr(item, "page_content", item) for item in payload
                                ]
                                return self._ed(normalized)
                        if isinstance(ts, (list, tuple)):
                            normalized = [
                                getattr(item, "page_content", item) for item in ts
                            ]
                            return self._ed(normalized)
                        # Fallback: coerce to string and embed as a query
                        return self._eq(str(ts))
                self.embeddings = _Emb(_embed_query, _embed_docs)
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            retriever = self.vector_store.as_retriever()
            
            return {
                "success": True,
                "vector_store": self.vector_store,
                "retriever": retriever,
                "metadata": {
                    "total_documents": len(documents),
                    "index_size": self.vector_store.index.ntotal if self.vector_store else 0
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        if self.vector_store:
            return self.vector_store.similarity_search(query, k=k)
        return []