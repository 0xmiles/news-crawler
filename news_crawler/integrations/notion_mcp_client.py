"""
Notion MCP client for adding summarized content to specific pages.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from news_crawler.crawlers.base import CrawledContent


class NotionMCPClient:
    """Notion MCP client for page management."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.notion.com/v1"
        
        # Debug: Log the API key being used
        api_key = config.get('api_key')
        self.logger.info(f"Using Notion API key: {api_key[:20]}..." if api_key else "No API key found")
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def add_summary_to_page(self, page_url: str, summary_data: Dict[str, Any]) -> bool:
        """Add summary content to a specific Notion page."""
        try:
            # Extract page ID from URL
            page_id = self._extract_page_id(page_url)
            if not page_id:
                self.logger.error(f"Could not extract page ID from URL: {page_url}")
                return False
            
            # Get current page content
            current_blocks = await self._get_page_blocks(page_id)
            
            # Create new summary block
            summary_block = self._create_summary_block(summary_data)
            
            # Add summary block to page
            success = await self._add_block_to_page(page_id, summary_block)
            
            if success:
                self.logger.info(f"Successfully added summary to page: {page_id}")
                return True
            else:
                self.logger.error(f"Failed to add summary to page: {page_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding summary to page: {e}")
            return False
    
    def _extract_page_id(self, page_url: str) -> Optional[str]:
        """Extract page ID from Notion page URL."""
        import re
        
        # Extract 32-character hex string from URL
        # This works for most Notion URL formats
        match = re.search(r'([a-f0-9]{32})', page_url)
        if match:
            return match.group(1)
        
        return None
    
    async def _get_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """Get current blocks from a Notion page."""
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"
            response = await self._make_request("GET", url)
            
            if response and response.get('results'):
                return response['results']
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting page blocks: {e}")
            return []
    
    async def _add_block_to_page(self, page_id: str, block_data: Dict[str, Any]) -> bool:
        """Add a block to a Notion page."""
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"
            
            # First add the main block
            main_block = block_data.get("main_block", block_data)
            payload = {"children": [main_block]}
            
            response = await self._make_request("PATCH", url, json=payload)
            if not response:
                return False
            
            # If there are children, add them to the main block
            children = block_data.get("children", [])
            if children:
                # Get the ID of the main block we just created
                main_block_id = response.get("results", [{}])[0].get("id")
                if main_block_id:
                    children_url = f"{self.base_url}/blocks/{main_block_id}/children"
                    children_payload = {"children": children}
                    await self._make_request("PATCH", children_url, json=children_payload)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding block to page: {e}")
            return False
    
    def _create_summary_block(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary block for Notion page."""
        title = summary_data.get('title', 'Untitled')
        summary = summary_data.get('summary', '')
        key_points = summary_data.get('key_points', [])
        url = summary_data.get('url', '')
        author = summary_data.get('author', '')
        published_date = summary_data.get('published_date', '')
        
        # Create the main summary block
        block = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📄 {title}"
                        }
                    }
                ]
            }
        }
        
        # Create children blocks separately
        children_blocks = []
        
        # Add summary content
        if summary:
            summary_block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"📝 요약: {summary}"
                            }
                        }
                    ]
                }
            }
            children_blocks.append(summary_block)
        
        # Add key points
        if key_points:
            key_points_block = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🔑 주요 포인트:"
                            }
                        }
                    ]
                }
            }
            children_blocks.append(key_points_block)
            
            for point in key_points:
                point_block = {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"• {point}"
                                }
                            }
                        ]
                    }
                }
                children_blocks.append(point_block)
        
        # Add metadata
        if url:
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"🔗 원본: {url}",
                                "link": {"url": url}
                            }
                        }
                    ]
                }
            })
        
        if author:
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"👤 작성자: {author}"
                            }
                        }
                    ]
                }
            })
        
        if published_date:
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"📅 발행일: {published_date}"
                            }
                        }
                    ]
                }
            })
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        children_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"⏰ 크롤링 시간: {timestamp}"
                        }
                    }
                ]
            }
        })
        
        # Return both the main block and children
        return {
            "main_block": block,
            "children": children_blocks
        }
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Notion API."""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=self.headers, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"HTTP {response.status}: {await response.text()}")
                        return None
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return None
    
    async def get_page_info(self, page_url: str) -> Optional[Dict[str, Any]]:
        """Get information about a Notion page."""
        try:
            page_id = self._extract_page_id(page_url)
            if not page_id:
                return None
            
            url = f"{self.base_url}/pages/{page_id}"
            response = await self._make_request("GET", url)
            
            if response:
                return {
                    'id': response.get('id'),
                    'title': self._extract_title_from_properties(response.get('properties', {})),
                    'url': response.get('url'),
                    'created_time': response.get('created_time'),
                    'last_edited_time': response.get('last_edited_time')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting page info: {e}")
            return None
    
    def _extract_title_from_properties(self, properties: Dict[str, Any]) -> str:
        """Extract title from Notion page properties."""
        title_property = properties.get('title') or properties.get('Title')
        if title_property and title_property.get('title'):
            title_array = title_property['title']
            if title_array:
                return title_array[0].get('plain_text', 'Untitled')
        return 'Untitled'
    
    async def test_connection(self) -> bool:
        """Test Notion API connection."""
        try:
            url = f"{self.base_url}/users/me"
            response = await self._make_request("GET", url)
            return response is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
