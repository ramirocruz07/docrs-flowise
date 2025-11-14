from pydantic import BaseModel
from typing import Dict, Any, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class TextSplitterNode:
    class Config(BaseModel):
        chunk_size: int = 1000
        chunk_overlap: int = 200
        name: str = "Text Splitter"
        
    def __init__(self, config: Config):
        self.type = "text_splitter"
        self.name = config.name
        self.inputs = ["documents"]
        self.outputs = ["chunks"]
        self.config = config
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
        )
        
    def process(self, documents: List[Document]) -> Dict[str, Any]:
        try:
            chunks = self.splitter.split_documents(documents)
            
            return {
                "success": True,
                "chunks": chunks,
                "metadata": {
                    "total_chunks": len(chunks),
                    "chunk_size": self.config.chunk_size,
                    "chunk_overlap": self.config.chunk_overlap
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }