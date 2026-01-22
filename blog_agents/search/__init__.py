"""Search provider for blog agents using Claude's web_search tool."""

from blog_agents.search.base_search import BaseSearchProvider, SearchResult
from blog_agents.search.claude_search import ClaudeSearchProvider

__all__ = [
    "BaseSearchProvider",
    "SearchResult",
    "ClaudeSearchProvider",
]
