"""Search configuration using Claude's web_search tool."""

from pydantic import BaseModel


class SearchConfig(BaseModel):
    """Search configuration for Claude web_search tool."""
    max_results: int = 10
