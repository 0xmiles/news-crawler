"""Google Custom Search API implementation."""

import aiohttp
import logging
from typing import List, Dict, Any
from blog_agents.search.base_search import BaseSearchProvider, SearchResult
from blog_agents.utils.retry import async_retry

logger = logging.getLogger(__name__)


class GoogleSearchProvider(BaseSearchProvider):
    """Google Custom Search API provider."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, search_engine_id: str, max_results: int = 10):
        """Initialize Google search provider.

        Args:
            api_key: Google API key
            search_engine_id: Custom Search Engine ID
            max_results: Maximum results to return
        """
        super().__init__(api_key, max_results)
        self.search_engine_id = search_engine_id

    @async_retry(max_attempts=3)
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute Google search.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results

        Raises:
            Exception: If search fails
        """
        # Validate query
        self.validate_query(query)

        # Limit results
        num_results = min(num_results, self.max_results)

        # Build request parameters
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": num_results
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Google API error {response.status}: {error_text}")

                    data = await response.json()

                    # Extract results
                    raw_results = self._parse_response(data)

                    # Format results
                    return self.format_results(raw_results, "google")

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            raise

    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Google API response.

        Args:
            data: Raw API response

        Returns:
            List of parsed results
        """
        results = []

        items = data.get("items", [])
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })

        return results
