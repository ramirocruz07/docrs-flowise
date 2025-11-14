from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os

class WebSearchNode:
    class Config(BaseModel):
        provider: str = "serpapi"  # "serpapi" or "brave"
        name: str = "Web Search"
        num_results: int = 5
        
    def __init__(self, config: Config, serpapi_key: Optional[str] = None, brave_key: Optional[str] = None):
        self.type = "web_search"
        self.name = config.name
        self.inputs = ["query"]
        self.outputs = ["search_results"]
        self.config = config
        
        provider = getattr(config, 'provider', 'serpapi') or 'serpapi'
        
        if provider == "brave":
            if not brave_key:
                raise ValueError("BRAVE_API_KEY environment variable is not set")
            self.api_key = brave_key
            self.provider = "brave"
        else:  # default to SerpAPI
            if not serpapi_key:
                raise ValueError("SERPAPI_KEY environment variable is not set")
            self.api_key = serpapi_key
            self.provider = "serpapi"
    
    def process(self, query: str) -> Dict[str, Any]:
        try:
            if self.provider == "brave":
                return self._search_brave(query)
            else:
                return self._search_serpapi(query)
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _search_serpapi(self, query: str) -> Dict[str, Any]:
        try:
            from serpapi import GoogleSearch
            
            search = GoogleSearch({
                "q": query,
                "api_key": self.api_key,
                "num": self.config.num_results or 5
            })
            results = search.get_dict()
            
            search_results = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    search_results.append({
                        "title": result.get("title", ""),
                        "link": result.get("link", ""),
                        "snippet": result.get("snippet", "")
                    })
            
            return {
                "success": True,
                "search_results": search_results,
                "metadata": {
                    "provider": "serpapi",
                    "num_results": len(search_results)
                }
            }
        except ImportError:
            return {
                "success": False,
                "error": "serpapi package not installed. Install with: pip install google-search-results"
            }
    
    def _search_brave(self, query: str) -> Dict[str, Any]:
        try:
            import requests
            
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": self.config.num_results or 5
            }
            
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            search_results = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"]:
                    search_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", "")
                    })
            
            return {
                "success": True,
                "search_results": search_results,
                "metadata": {
                    "provider": "brave",
                    "num_results": len(search_results)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Brave search failed: {str(e)}"
            }






