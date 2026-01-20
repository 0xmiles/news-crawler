"""Bing Web Search API implementation."""

import aiohttp
import logging
from typing import List, Dict, Any
from blog_agents.search.base_search import BaseSearchProvider, SearchResult
from blog_agents.utils.retry import async_retry

logger = logging.getLogger(__name__)


class BingSearchProvider(BaseSearchProvider):
    """Bing Web Search API provider."""

    BASE_URL = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(self, api_key: str, max_results: int = 10, market: str = "en-US"):
        """Initialize Bing search provider.

        Args:
            api_key: Bing API key
            max_results: Maximum results to return
            market: Market/locale (e.g., "en-US")
        """
        super().__init__(api_key, max_results)
        self.market = market

    @async_retry(max_attempts=3)
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute Bing search.

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
            "q": query,
            "count": num_results,
            "mkt": self.market
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Bing API error {response.status}: {error_text}")

                    data = await response.json()

                    # Extract results
                    raw_results = self._parse_response(data)

                    # Format results
                    return self.format_results(raw_results, "bing")

        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            raise

    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Bing API response.

        Args:
            data: Raw API response

        Returns:
            List of parsed results
        """
        results = []

        web_pages = data.get("webPages", {})
        values = web_pages.get("value", [])

        for item in values:
            results.append({
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", "")
            })

        return results
