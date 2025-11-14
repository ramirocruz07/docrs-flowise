"""
Component Configuration Panel - Defines configuration schemas for each node type
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class APIProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


class WebSearchProvider(str, Enum):
    SERPAPI = "serpapi"
    BRAVE = "brave"


class NodeConfigSchema:
    """Configuration schemas for different node types"""
    
    @staticmethod
    def get_schema(node_type: str) -> Dict[str, Any]:
        """Get configuration schema for a node type"""
        schemas = {
            "pdf_loader": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "PDF Loader",
                        "required": False
                    }
                ]
            },
            "text_splitter": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "Text Splitter",
                        "required": False
                    },
                    {
                        "name": "chunk_size",
                        "label": "Chunk Size",
                        "type": "number",
                        "default": 1000,
                        "required": False,
                        "min": 100,
                        "max": 10000
                    },
                    {
                        "name": "chunk_overlap",
                        "label": "Chunk Overlap",
                        "type": "number",
                        "default": 200,
                        "required": False,
                        "min": 0,
                        "max": 1000
                    }
                ]
            },
            "embeddings": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "Embeddings",
                        "required": False
                    },
                    {
                        "name": "provider",
                        "label": "API Provider",
                        "type": "select",
                        "options": [
                            {"value": "openai", "label": "OpenAI"},
                            {"value": "gemini", "label": "Google Gemini"}
                        ],
                        "default": "openai",
                        "required": True
                    },
                    {
                        "name": "model",
                        "label": "Model",
                        "type": "text",
                        "default": "text-embedding-ada-002",
                        "required": False,
                        "conditional": {
                            "field": "provider",
                            "openai": {"default": "text-embedding-ada-002"},
                            "gemini": {"default": "models/embedding-001"}
                        }
                    }
                ]
            },
            "vector_store": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "Vector Store",
                        "required": False
                    },
                    {
                        "name": "provider",
                        "label": "Embedding Provider",
                        "type": "select",
                        "options": [
                            {"value": "openai", "label": "OpenAI"},
                            {"value": "gemini", "label": "Google Gemini"}
                        ],
                        "default": "openai",
                        "required": True
                    }
                ]
            },
            "qa_chain": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "QA Chain",
                        "required": False
                    },
                    {
                        "name": "provider",
                        "label": "API Provider",
                        "type": "select",
                        "options": [
                            {"value": "openai", "label": "OpenAI"},
                            {"value": "gemini", "label": "Google Gemini"}
                        ],
                        "default": "openai",
                        "required": True
                    },
                    {
                        "name": "model",
                        "label": "Model",
                        "type": "text",
                        "default": "gpt-3.5-turbo",
                        "required": False,
                        "conditional": {
                            "field": "provider",
                            "openai": {"default": "gpt-3.5-turbo"},
                            "gemini": {"default": "gemini-pro"}
                        }
                    },
                    {
                        "name": "temperature",
                        "label": "Temperature",
                        "type": "number",
                        "default": 0,
                        "required": False,
                        "min": 0,
                        "max": 2,
                        "step": 0.1
                    }
                ]
            },
            "web_search": {
                "fields": [
                    {
                        "name": "name",
                        "label": "Node Name",
                        "type": "text",
                        "default": "Web Search",
                        "required": False
                    },
                    {
                        "name": "provider",
                        "label": "Search Provider",
                        "type": "select",
                        "options": [
                            {"value": "serpapi", "label": "SerpAPI"},
                            {"value": "brave", "label": "Brave Search"}
                        ],
                        "default": "serpapi",
                        "required": True
                    },
                    {
                        "name": "num_results",
                        "label": "Number of Results",
                        "type": "number",
                        "default": 5,
                        "required": False,
                        "min": 1,
                        "max": 20
                    }
                ]
            }
        }
        
        return schemas.get(node_type, {"fields": []})
    
    @staticmethod
    def get_default_config(node_type: str) -> Dict[str, Any]:
        """Get default configuration for a node type"""
        schema = NodeConfigSchema.get_schema(node_type)
        config = {}
        
        for field in schema.get("fields", []):
            if "default" in field:
                config[field["name"]] = field["default"]
        
        return config





