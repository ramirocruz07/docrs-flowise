from pydantic import BaseModel
from typing import Dict, Any, Optional
# Support both new (>=1.x) and legacy (0.27.x) OpenAI SDKs
try:
    from openai import OpenAI  # new SDK
    _OPENAI_SDK = "new"
except Exception:  # pragma: no cover
    OpenAI = None
    _OPENAI_SDK = "legacy"
    import openai as openai_legacy  # legacy SDK

class EmbeddingsNode:
    class Config(BaseModel):
        # Provider kept for UI compatibility; backend always uses OpenAI
        provider: str = "openai"
        model: str = "text-embedding-ada-002"
        name: str = "Embeddings"
        
    def __init__(self, config: Config, api_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.type = "embeddings"
        self.name = config.name
        self.inputs = ["text"]
        self.outputs = ["embeddings"]
        self.config = config
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.model = config.model or "text-embedding-ada-002"
        self.api_key = api_key
        # Lazy-create client in process() to avoid constructor-time SDK issues
        
    def process(self, text: str) -> Dict[str, Any]:
        try:
            # Lazy init client per call for maximum compatibility
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
                client = OpenAI(**client_kwargs)
                response = client.embeddings.create(model=self.model, input=text)
                embedding = response.data[0].embedding
            else:
                response = openai_legacy.Embedding.create(model=self.model, input=text)
                embedding = response["data"][0]["embedding"]
            
            return {
                "success": True,
                "embedding": embedding,
                "metadata": {
                    "model": self.config.model,
                    "embedding_dim": len(embedding)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }