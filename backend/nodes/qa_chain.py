from pydantic import BaseModel
from typing import Dict, Any, Optional
try:
    from openai import OpenAI  # new SDK
    _OPENAI_SDK = "new"
except Exception:  # pragma: no cover
    OpenAI = None
    _OPENAI_SDK = "legacy"
    import openai as openai_legacy

class QAChainNode:
    class Config(BaseModel):
        # Provider kept for UI compatibility; backend always uses OpenAI
        provider: str = "openai"
        model: str = "gpt-3.5-turbo"
        temperature: float = 0
        name: str = "QA Chain"
        
    def __init__(self, config: Config, api_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.type = "qa_chain"
        self.name = config.name
        self.inputs = ["retriever", "question", "custom_prompt"]
        self.outputs = ["answer"]
        self.config = config
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.model = config.model or "gpt-3.5-turbo"
        self.api_key = api_key
        # Defer client creation until initialize_chain/process to avoid constructor-time issues
        self.client = None
        self.qa_chain = None
        
    def initialize_chain(self, retriever):
        # Store retriever; prompt rendered directly during process()
        self.retriever = retriever
        self.prompt_template = (
            "Use the following context to answer the question. "
            "If the answer is not in the context, say you don't know.\n\n"
            "CONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER:"
        )
        # Lazily initialize client here
        if self.client is None:
            if _OPENAI_SDK == "new":
                # Initialize with minimal config to avoid proxy/environment issues
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
                self.client = OpenAI(**client_kwargs)
            else:
                openai_legacy.api_key = self.api_key
        
    def process(self, question: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not hasattr(self, "retriever") or self.retriever is None:
                return {
                    "success": False,
                    "error": "QA chain not initialized. Please connect to a retriever first."
                }
            # Lazily ensure client exists (in case initialize_chain wasn't called yet)
            if self.client is None:
                if _OPENAI_SDK == "new":
                    # Initialize with minimal config to avoid proxy/environment issues
                    import os
                    client_kwargs = {"api_key": self.api_key}
                    if os.getenv("OPENAI_TIMEOUT"):
                        try:
                            client_kwargs["timeout"] = float(os.getenv("OPENAI_TIMEOUT"))
                        except (ValueError, TypeError):
                            pass
                    self.client = OpenAI(**client_kwargs)
                else:
                    openai_legacy.api_key = self.api_key
            # Retrieve documents and build context (support both LC 0.0.x and 0.2 Runnables)
            if hasattr(self.retriever, "get_relevant_documents"):
                docs = self.retriever.get_relevant_documents(question)
            elif hasattr(self.retriever, "invoke"):
                maybe_docs = self.retriever.invoke(question)
                docs = maybe_docs if isinstance(maybe_docs, list) else []
            else:
                docs = []
            # Normalize docs robustly: handle tuples/lists/dicts/nested structures
            def _coerce_doc(x):
                # Dict payloads
                if isinstance(x, dict):
                    if "document" in x:
                        return _coerce_doc(x["document"])
                    if "doc" in x:
                        return _coerce_doc(x["doc"])
                    return x
                # Tuples/lists like (Document, score, *rest) or nested
                if isinstance(x, (tuple, list)) and len(x) > 0:
                    return _coerce_doc(x[0])
                return x
            if isinstance(docs, dict):
                docs = docs.get("documents") or docs.get("docs") or []
            if not isinstance(docs, list):
                docs = list(docs) if docs is not None else []
            docs = [_coerce_doc(d) for d in docs]
            context = "\n\n".join([getattr(d, "page_content", str(d)) for d in (docs[:6] if isinstance(docs, list) else [])])
            template = self.prompt_template
            if custom_prompt:
                custom_prompt = custom_prompt.strip()
                if custom_prompt:
                    template = (
                        f"{custom_prompt.rstrip()}\n\n"
                        "-----\n\n"
                        f"{self.prompt_template}"
                    )
            prompt = template.format(context=context, question=question)
            # Call OpenAI chat completions directly
            if _OPENAI_SDK == "new":
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=800,
                )
                answer = resp.choices[0].message.content.strip()
            else:
                resp = openai_legacy.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=800,
                )
                answer = resp["choices"][0]["message"]["content"].strip()
            # Collect simple source hints
            sources = []
            for doc in docs:
                meta = getattr(doc, "metadata", {}) or {}
                if "page" in meta:
                    sources.append(f"Page {meta['page'] + 1}")
            return {
                "success": True,
                "answer": answer,
                "sources": list(set(sources)),
                "metadata": {
                    "model": self.config.model,
                    "temperature": self.config.temperature
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }