"""Search provider specific configurations."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class GoogleSearchConfig(BaseModel):
    """Google Custom Search API configuration."""
    api_key: str
    search_engine_id: str
    max_results: int = 10

    # Search parameters
    language: str = "lang_en"
    safe_search: str = "off"
    file_type: str = ""  # e.g., "pdf", "doc", etc.

    def to_params(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Convert to API request parameters.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            Dictionary of API parameters
        """
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": min(num_results, self.max_results),
        }

        if self.language:
            params["lr"] = self.language
        if self.safe_search:
            params["safe"] = self.safe_search
        if self.file_type:
            params["fileType"] = self.file_type

        return params


class BingSearchConfig(BaseModel):
    """Bing Web Search API configuration."""
    api_key: str
    max_results: int = 10

    # Search parameters
    market: str = "en-US"
    safe_search: str = "Moderate"  # Off, Moderate, Strict
    freshness: str = ""  # Day, Week, Month

    def to_params(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Convert to API request parameters.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            Dictionary of API parameters
        """
        params = {
            "q": query,
            "count": min(num_results, self.max_results),
            "mkt": self.market,
            "safeSearch": self.safe_search,
        }

        if self.freshness:
            params["freshness"] = self.freshness

        return params

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Bing API.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Ocp-Apim-Subscription-Key": self.api_key
        }


def create_search_config(provider: str, api_key: str, **kwargs) -> GoogleSearchConfig | BingSearchConfig:
    """Factory function to create search configuration.

    Args:
        provider: Search provider ("google" or "bing")
        api_key: API key for the provider
        **kwargs: Additional configuration parameters

    Returns:
        Search configuration object

    Raises:
        ValueError: If provider is not supported
    """
    if provider == "google":
        if "search_engine_id" not in kwargs:
            raise ValueError("Google search requires 'search_engine_id'")
        return GoogleSearchConfig(api_key=api_key, **kwargs)
    elif provider == "bing":
        return BingSearchConfig(api_key=api_key, **kwargs)
    else:
        raise ValueError(f"Unsupported search provider: {provider}")
