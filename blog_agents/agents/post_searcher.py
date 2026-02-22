"""PostSearcher agent for finding relevant articles using Claude's web_search."""

import asyncio
import logging
import json
from typing import Dict, Any, List
import aiohttp
from bs4 import BeautifulSoup
from blog_agents.core.base_agent import BaseAgent
from blog_agents.config.agent_config import Config
from blog_agents.search.claude_search import ClaudeSearchProvider
from blog_agents.utils.file_manager import FileManager
from blog_agents.core.communication import SearchResultsMessage

logger = logging.getLogger(__name__)


class PostSearcher(BaseAgent):
    """Agent for searching and ranking relevant articles."""

    def __init__(self, config: Config):
        """Initialize PostSearcher.

        Args:
            config: System configuration
        """
        super().__init__(config, "PostSearcher")

        # Initialize search provider - using Claude's web_search tool
        self.search_provider = ClaudeSearchProvider(
            claude_api_key=config.claude.api_key,
            max_results=config.search.max_results
        )
        logger.info("Using Claude web search (Anthropic API web_search_20250305 tool)")

        self.file_manager = FileManager(config.blog_agents.output_dir)
        self.max_articles = config.blog_agents.post_searcher.max_articles
        self.min_content_length = config.blog_agents.post_searcher.min_content_length

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search and ranking.

        Args:
            input_data: Must contain 'keywords' key

        Returns:
            Dictionary with search results and metadata
        """
        keywords = input_data.get("keywords", "")
        if not keywords:
            raise ValueError("Keywords are required")

        # Step 1: Execute search
        logger.info(f"Searching for: {keywords}")
        search_results = await self.search_provider.search(
            query=keywords,
            num_results=self.config.search.max_results
        )

        logger.info(f"Found {len(search_results)} results")

        # Step 2: Extract content from URLs
        articles = await self._extract_content(search_results)
        logger.info(f"Extracted content from {len(articles)} articles")

        # Step 3: Rank by relevance using Claude
        ranked_articles = await self._rank_articles(keywords, articles)
        logger.info(f"Ranked {len(ranked_articles)} articles")

        # Step 4: Select top articles
        selected_articles = ranked_articles[:self.max_articles]
        logger.info(f"Selected top {len(selected_articles)} articles")

        # Step 5: Save results
        output_data = {
            "query": keywords,
            "total_found": len(search_results),
            "articles_extracted": len(articles),
            "selected_count": len(selected_articles),
            "selected_articles": selected_articles
        }

        # Save to file
        await self.file_manager.write_json("search_results.json", output_data)

        return output_data

    async def _extract_content(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Extract content from search result URLs concurrently.

        Uses asyncio.gather with a semaphore to fetch all URLs in parallel
        while limiting simultaneous connections to avoid overwhelming servers.

        Args:
            search_results: List of search results

        Returns:
            List of articles with extracted content
        """
        semaphore = asyncio.Semaphore(5)

        async def fetch_with_limit(result: Any) -> Dict[str, Any] | None:
            async with semaphore:
                try:
                    content = await self._fetch_url_content(result.url)
                    if len(content) < self.min_content_length:
                        logger.debug(f"Skipping {result.url} - content too short")
                        return None
                    return {
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "content": content,
                        "source": result.source
                    }
                except Exception as e:
                    logger.warning(f"Failed to extract content from {result.url}: {e}")
                    return None

        raw_results = await asyncio.gather(
            *[fetch_with_limit(r) for r in search_results],
            return_exceptions=False,
        )

        return [article for article in raw_results if article is not None]

    async def _fetch_url_content(self, url: str, session: aiohttp.ClientSession | None = None) -> str:
        """Fetch and parse content from URL.

        Args:
            url: URL to fetch
            session: Optional shared aiohttp session. Creates a one-off session if not provided.

        Returns:
            Extracted text content
        """
        async def _do_fetch(s: aiohttp.ClientSession) -> str:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                html = await response.text()

                soup = BeautifulSoup(html, 'lxml')
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                text = soup.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return '\n'.join(lines)

        if session is not None:
            return await _do_fetch(session)

        async with aiohttp.ClientSession() as new_session:
            return await _do_fetch(new_session)

    async def _rank_articles(self, keywords: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank articles by relevance using Claude.

        Args:
            keywords: Search keywords
            articles: List of articles to rank

        Returns:
            Sorted list of articles (most relevant first)
        """
        if not articles:
            return []

        # Prepare article summaries for ranking
        article_summaries = []
        for idx, article in enumerate(articles):
            # Truncate content for ranking
            content_preview = article['content'][:1000]
            article_summaries.append({
                "index": idx,
                "title": article['title'],
                "url": article['url'],
                "snippet": article['snippet'],
                "content_preview": content_preview
            })

        # Create ranking prompt
        system_prompt = """You are a content curator. Rank the provided articles by their relevance to the given keywords.

Consider:
1. Topical relevance to keywords
2. Content quality and depth
3. Recency and credibility

Respond with a JSON array of indices in order of relevance (most relevant first).
Example: [2, 0, 4, 1, 3]"""

        user_message = f"""Keywords: {keywords}

Articles:
{json.dumps(article_summaries, indent=2)}

Rank these articles by relevance. Respond with only the JSON array of indices."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                cache_system=True,
            )

            # Parse ranking
            ranking = self._extract_ranking(response)

            # Reorder articles
            ranked_articles = []
            for idx in ranking:
                if 0 <= idx < len(articles):
                    article = articles[idx].copy()
                    article['relevance_rank'] = len(ranked_articles) + 1
                    ranked_articles.append(article)

            # Add any missing articles at the end
            ranked_indices = set(ranking)
            for idx, article in enumerate(articles):
                if idx not in ranked_indices:
                    article = article.copy()
                    article['relevance_rank'] = len(ranked_articles) + 1
                    ranked_articles.append(article)

            return ranked_articles

        except Exception as e:
            logger.error(f"Ranking failed: {e}")
            # Fall back to original order
            for idx, article in enumerate(articles):
                article['relevance_rank'] = idx + 1
            return articles

    def _extract_ranking(self, response: str) -> List[int]:
        """Extract ranking indices from Claude response.

        Args:
            response: Claude's response text

        Returns:
            List of indices
        """
        try:
            # Try to parse as JSON
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to find JSON array in response
            import re
            pattern = r'\[[\d,\s]+\]'
            matches = re.findall(pattern, response)
            if matches:
                return json.loads(matches[0])

            # Fall back to sequential order
            logger.warning("Could not parse ranking, using original order")
            return list(range(10))  # Assume max 10 articles
