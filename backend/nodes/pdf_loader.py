from pydantic import BaseModel
from typing import Dict, Any, List
import tempfile
import aiofiles
from langchain_community.document_loaders import PyPDFLoader

class PDFLoaderNode:
    class Config(BaseModel):
        name: str = "PDF Loader"
        
    def __init__(self):
        self.type = "pdf_loader"
        self.name = "PDF Loader"
        self.inputs = ["file_path"]
        self.outputs = ["documents"]
        
    async def process(self, file_content: bytes) -> Dict[str, Any]:
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Load PDF
            loader = PyPDFLoader(temp_file_path)
            documents = loader.load()
            
            return {
                "success": True,
                "documents": documents,
                "metadata": {
                    "total_pages": len(documents),
                    "file_name": temp_file_path
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }