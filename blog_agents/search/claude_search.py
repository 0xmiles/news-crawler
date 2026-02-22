"""Claude Web Search implementation using Anthropic API's web_search tool.

This provider uses Claude API's built-in web_search_20250305 tool,
eliminating the need for external search API keys.
"""

import logging
import json
from typing import List, Dict, Any
import anthropic
from anthropic import AsyncAnthropic
from blog_agents.search.base_search import BaseSearchProvider, SearchResult
from blog_agents.utils.retry import async_retry

logger = logging.getLogger(__name__)


class ClaudeSearchProvider(BaseSearchProvider):
    """Search provider using Anthropic API's web_search tool.

    This provider leverages Claude's native web search tool (web_search_20250305),
    which means:
    - No external search API keys needed
    - High-quality, AI-curated results
    - Automatically filtered and ranked by relevance
    - Only requires Claude API key
    """

    def __init__(self, claude_api_key: str, max_results: int = 10):
        """Initialize Claude search provider.

        Args:
            claude_api_key: Anthropic API key for Claude
            max_results: Maximum results to return
        """
        # Clean up inputs
        claude_api_key = claude_api_key.strip() if claude_api_key else ""

        super().__init__(claude_api_key, max_results)

        # Validate inputs
        if not claude_api_key:
            raise ValueError("Claude API key is required")

        self.client = AsyncAnthropic(api_key=claude_api_key)
        logger.info("Initialized ClaudeSearchProvider (using Anthropic web_search tool)")

    @async_retry(max_attempts=3)
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute web search using Claude's web_search tool.

        Args:
            query: Search query string
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

        logger.info(f"Executing Claude web search: query='{query}', num={num_results}")

        try:
            # Create a message with web_search tool enabled
            search_prompt = f"""Search the web for: "{query}"

Please provide {num_results} relevant search results. For each result, include:
1. The page title
2. The URL
3. A brief snippet or description

Format your response as a JSON array like this:
[
    {{
        "title": "Page title",
        "url": "https://example.com",
        "snippet": "Brief description"
    }}
]"""

            # Call Claude with web_search tool
            response = await self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": search_prompt
                    }
                ],
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": max(5, num_results)  # Allow enough searches
                    }
                ],
                temperature=0.3,
            )

            logger.debug(f"Claude response stop_reason: {response.stop_reason}")

            # Parse response and extract search results
            raw_results = self._parse_claude_response(response, query)

            logger.info(f"Found {len(raw_results)} results from Claude web search")

            # Format results
            formatted_results = self.format_results(raw_results, "claude")

            # Limit to requested number
            return formatted_results[:num_results]

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise Exception(f"Claude API error: {e}")
        except Exception as e:
            logger.error(f"Claude web search failed: {e}")
            raise

    def _parse_claude_response(self, response: anthropic.types.AsyncMessage, query: str) -> List[Dict[str, Any]]:
        """Parse Claude's response to extract search results.

        Args:
            response: Claude API response message
            query: Original search query

        Returns:
            List of parsed results
        """
        results = []

        try:
            # Process all content blocks
            for content_block in response.content:
                # Check for text content with search results
                if hasattr(content_block, 'text') and content_block.text:
                    text = content_block.text.strip()

                    # Try to parse as JSON
                    try:
                        # Remove markdown code blocks if present
                        if text.startswith("```"):
                            lines = text.split("\n")
                            # Remove first line (```json or ```)
                            lines = lines[1:]
                            # Remove last line (```)
                            if lines and lines[-1].strip() == "```":
                                lines = lines[:-1]
                            text = "\n".join(lines).strip()

                        # Try to parse as JSON array
                        if text.startswith("["):
                            parsed_results = json.loads(text)
                            if isinstance(parsed_results, list):
                                for result in parsed_results:
                                    if isinstance(result, dict):
                                        title = result.get("title", "")
                                        url = result.get("url", "")
                                        snippet = result.get("snippet", "")

                                        if title and url:
                                            results.append({
                                                "title": title,
                                                "url": url,
                                                "snippet": snippet
                                            })
                        # Try to parse as JSON object
                        elif text.startswith("{"):
                            parsed_result = json.loads(text)
                            if "results" in parsed_result:
                                for result in parsed_result["results"]:
                                    if isinstance(result, dict):
                                        title = result.get("title", "")
                                        url = result.get("url", "")
                                        snippet = result.get("snippet", "")

                                        if title and url:
                                            results.append({
                                                "title": title,
                                                "url": url,
                                                "snippet": snippet
                                            })

                    except json.JSONDecodeError:
                        # Not JSON, might be natural language response
                        # Extract URLs and titles from text
                        logger.debug("Response not in JSON format, Claude may have used web_search tool")
                        continue

                # Check for tool_use blocks (web_search results)
                elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    if content_block.name == 'web_search':
                        logger.debug(f"Found web_search tool use: {content_block.id}")
                        # Tool results are typically in subsequent assistant turns
                        # or we need to process them differently

            # If we got results from parsing, return them
            if results:
                return results

            # If no structured results, try to extract from any text content
            all_text = ""
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    all_text += content_block.text + "\n"

            # Extract URLs and titles from natural language response
            if all_text and not results:
                logger.debug("Attempting to extract results from natural language response")
                # This is a fallback - ideally we get structured data
                import re

                # Find URLs in text
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, all_text)

                # Create basic results from URLs
                for i, url in enumerate(urls[:self.max_results]):
                    results.append({
                        "title": f"Search result {i+1} for: {query}",
                        "url": url,
                        "snippet": "Web search result"
                    })

        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.debug(f"Response content: {response.content}")

        return results
