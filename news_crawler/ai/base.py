"""
Base AI client interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging


class BaseAIClient(ABC):
    """Base AI client interface."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def summarize(self, content: str, max_length: int = 500) -> str:
        """Summarize content."""
        pass
    
    @abstractmethod
    async def extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content."""
        pass
    
    @abstractmethod
    async def generate_title(self, content: str) -> str:
        """Generate a title for content."""
        pass
    
    @abstractmethod
    async def categorize_content(self, content: str, categories: List[str]) -> str:
        """Categorize content into predefined categories."""
        pass
    
    @abstractmethod
    async def translate(self, content: str, target_language: str = "en") -> str:
        """Translate content to target language."""
        pass
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limits."""
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content
        
        # Truncate and add ellipsis
        truncated = content[:max_chars - 3]
        # Try to break at sentence boundary
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.8:  # If we can break at a reasonable point
            truncated = truncated[:last_period + 1]
        
        return truncated + "..."
    
    def _clean_content_for_ai(self, content: str) -> str:
        """Clean content before sending to AI."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        import re
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML tags if any
        content = re.sub(r'<[^>]+>', '', content)
        
        # Limit length to prevent token overflow
        max_length = self.config.get('max_content_length', 50000)
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content.strip()
