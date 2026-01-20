"""Base search interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result model."""
    title: str
    url: str
    snippet: str
    position: int
    source: str  # "google" or "bing"


class BaseSearchProvider(ABC):
    """Abstract base class for search providers."""

    def __init__(self, api_key: str, max_results: int = 10):
        """Initialize search provider.

        Args:
            api_key: API key for search provider
            max_results: Maximum number of results to return
        """
        self.api_key = api_key
        self.max_results = max_results

    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute search query.

        Args:
            query: Search query string
            num_results: Number of results to return

        Returns:
            List of search results

        Raises:
            Exception: If search fails
        """
        pass

    def validate_query(self, query: str) -> bool:
        """Validate search query.

        Args:
            query: Query to validate

        Returns:
            True if valid

        Raises:
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if len(query) > 500:
            raise ValueError("Search query is too long (max 500 characters)")

        return True

    def format_results(self, raw_results: List[Dict[str, Any]], source: str) -> List[SearchResult]:
        """Format raw API results into SearchResult objects.

        Args:
            raw_results: Raw results from API
            source: Source name ("google" or "bing")

        Returns:
            List of formatted search results
        """
        results = []
        for idx, item in enumerate(raw_results):
            try:
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    position=idx + 1,
                    source=source
                )
                results.append(result)
            except Exception as e:
                # Skip invalid results
                continue

        return results
