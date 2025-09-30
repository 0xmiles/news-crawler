"""
Anthropic client for AI operations.
"""

import asyncio
from typing import Dict, Any, List, Optional
import anthropic
from news_crawler.ai.base import BaseAIClient


class AnthropicClient(BaseAIClient):
    """Anthropic client for AI operations."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(
            api_key=config.get('api_key'),
            timeout=60.0
        )
        self.model = config.get('model', 'claude-3-sonnet-20240229')
        self.max_tokens = config.get('max_tokens', 4000)
        self.temperature = config.get('temperature', 0.7)
    
    async def summarize(self, content: str, max_length: int = 500) -> str:
        """Summarize content using Anthropic."""
        try:
            content = self._clean_content_for_ai(content)
            if not content:
                return "No content to summarize."
            
            # Truncate content to fit within token limits
            max_input_tokens = self.max_tokens - 200
            content = self._truncate_content(content, max_input_tokens)
            
            prompt = f"""
Please provide a concise summary of the following content in approximately {max_length} characters or less. 
Focus on the main points, key insights, and important information. 
Write in a clear, professional tone suitable for a technical audience.

Content:
{content}
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=min(max_length // 2, 1000),
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            summary = response.content[0].text.strip()
            return summary if summary else "Unable to generate summary."
            
        except Exception as e:
            self.logger.error(f"Error summarizing content with Anthropic: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content."""
        try:
            content = self._clean_content_for_ai(content)
            if not content:
                return []
            
            max_input_tokens = self.max_tokens - 200
            content = self._truncate_content(content, max_input_tokens)
            
            prompt = f"""
Extract the key points from the following content. Return them as a numbered list of the most important points. 
Focus on technical insights, main arguments, and actionable information.

Content:
{content}
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            result = response.content[0].text.strip()
            
            # Parse numbered list
            key_points = []
            for line in result.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-') or line.startswith('*')):
                    # Remove numbering/bullets
                    clean_line = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '•', '-', '*']:
                        if clean_line.startswith(prefix):
                            clean_line = clean_line[len(prefix):].strip()
                            break
                    if clean_line:
                        key_points.append(clean_line)
            
            return key_points[:10]  # Limit to 10 key points
            
        except Exception as e:
            self.logger.error(f"Error extracting key points with Anthropic: {e}")
            return [f"Error extracting key points: {str(e)}"]
    
    async def generate_title(self, content: str) -> str:
        """Generate a title for content."""
        try:
            content = self._clean_content_for_ai(content)
            if not content:
                return "Untitled"
            
            max_input_tokens = self.max_tokens - 200
            content = self._truncate_content(content, max_input_tokens)
            
            prompt = f"""
Generate a clear, descriptive title for the following content. The title should be:
- Concise (under 100 characters)
- Descriptive of the main topic
- Professional and engaging
- Suitable for a technical audience

Content:
{content}
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            title = response.content[0].text.strip()
            return title if title else "Untitled"
            
        except Exception as e:
            self.logger.error(f"Error generating title with Anthropic: {e}")
            return "Untitled"
    
    async def categorize_content(self, content: str, categories: List[str]) -> str:
        """Categorize content into predefined categories."""
        try:
            content = self._clean_content_for_ai(content)
            if not content:
                return "Uncategorized"
            
            max_input_tokens = self.max_tokens - 200
            content = self._truncate_content(content, max_input_tokens)
            
            categories_str = ", ".join(categories)
            prompt = f"""
Categorize the following content into one of these categories: {categories_str}

Return only the category name that best fits the content.

Content:
{content}
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            category = response.content[0].text.strip()
            
            # Validate category
            if category in categories:
                return category
            else:
                # Find closest match
                for cat in categories:
                    if cat.lower() in category.lower() or category.lower() in cat.lower():
                        return cat
                return categories[0] if categories else "Uncategorized"
            
        except Exception as e:
            self.logger.error(f"Error categorizing content with Anthropic: {e}")
            return "Uncategorized"
    
    async def translate(self, content: str, target_language: str = "en") -> str:
        """Translate content to target language."""
        try:
            content = self._clean_content_for_ai(content)
            if not content:
                return ""
            
            max_input_tokens = self.max_tokens - 200
            content = self._truncate_content(content, max_input_tokens)
            
            prompt = f"""
Translate the following content to {target_language}. Maintain the original meaning and technical accuracy.

Content:
{content}
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            translation = response.content[0].text.strip()
            return translation if translation else content
            
        except Exception as e:
            self.logger.error(f"Error translating content with Anthropic: {e}")
            return content
