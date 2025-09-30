"""
AI-powered content summarization.
"""

import logging
from typing import List, Dict, Any, Optional
from news_crawler.ai.openai_client import OpenAIClient
from news_crawler.ai.anthropic_client import AnthropicClient


class Summarizer:
    """AI-powered content summarizer."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI client based on provider
        provider = config.get('provider', 'openai')
        if provider == 'openai':
            self.ai_client = OpenAIClient(config)
        elif provider == 'anthropic':
            self.ai_client = AnthropicClient(config)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    async def summarize(self, content: str, max_length: int = 500) -> str:
        """Summarize content using AI."""
        try:
            return await self.ai_client.summarize(content, max_length)
        except Exception as e:
            self.logger.error(f"Error summarizing content: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content."""
        try:
            return await self.ai_client.extract_key_points(content)
        except Exception as e:
            self.logger.error(f"Error extracting key points: {e}")
            return [f"Error extracting key points: {str(e)}"]
    
    async def generate_title(self, content: str) -> str:
        """Generate a title for content."""
        try:
            return await self.ai_client.generate_title(content)
        except Exception as e:
            self.logger.error(f"Error generating title: {e}")
            return "Untitled"
    
    async def categorize_content(self, content: str, categories: List[str]) -> str:
        """Categorize content into predefined categories."""
        try:
            return await self.ai_client.categorize_content(content, categories)
        except Exception as e:
            self.logger.error(f"Error categorizing content: {e}")
            return "Uncategorized"
    
    async def translate(self, content: str, target_language: str = "en") -> str:
        """Translate content to target language."""
        try:
            return await self.ai_client.translate(content, target_language)
        except Exception as e:
            self.logger.error(f"Error translating content: {e}")
            return content
