"""
Notion integration for uploading summaries and content.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from dataclasses import dataclass


@dataclass
class NotionPage:
    """Represents a Notion page."""
    title: str
    content: str
    url: Optional[str] = None
    tags: List[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class NotionClient:
    """Notion API client for uploading content."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = config.get('api_key')
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def create_page(self, page: NotionPage, database_id: str) -> Optional[str]:
        """Create a new page in Notion database."""
        try:
            url = f"{self.base_url}/pages"
            
            # Prepare page properties
            properties = self._build_properties(page)
            
            # Prepare page content (children blocks)
            children = self._build_content_blocks(page.content)
            
            payload = {
                "parent": {"database_id": database_id},
                "properties": properties,
                "children": children
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            page_data = response.json()
            page_id = page_data.get('id')
            
            self.logger.info(f"Successfully created Notion page: {page_id}")
            return page_id
            
        except Exception as e:
            self.logger.error(f"Error creating Notion page: {e}")
            return None
    
    def _build_properties(self, page: NotionPage) -> Dict[str, Any]:
        """Build Notion page properties."""
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": page.title
                        }
                    }
                ]
            }
        }
        
        # Add URL if available
        if page.url:
            properties["URL"] = {
                "url": page.url
            }
        
        # Add author if available
        if page.author:
            properties["Author"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": page.author
                        }
                    }
                ]
            }
        
        # Add published date if available
        if page.published_date:
            properties["Published Date"] = {
                "date": {
                    "start": page.published_date.isoformat()
                }
            }
        
        # Add tags if available
        if page.tags:
            properties["Tags"] = {
                "multi_select": [
                    {"name": tag} for tag in page.tags
                ]
            }
        
        # Add source type
        source_type = page.metadata.get('source', 'unknown')
        properties["Source Type"] = {
            "select": {
                "name": source_type
            }
        }
        
        # Add content length
        properties["Content Length"] = {
            "number": len(page.content)
        }
        
        return properties
    
    def _build_content_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Build Notion content blocks from text content."""
        blocks = []
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Create paragraph block
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": paragraph
                            }
                        }
                    ]
                }
            }
            blocks.append(block)
        
        return blocks
    
    async def update_page(self, page_id: str, page: NotionPage) -> bool:
        """Update an existing Notion page."""
        try:
            # Update page properties
            properties = self._build_properties(page)
            properties_url = f"{self.base_url}/pages/{page_id}"
            
            properties_payload = {"properties": properties}
            response = requests.patch(properties_url, headers=self.headers, json=properties_payload)
            response.raise_for_status()
            
            # Update page content
            await self._update_page_content(page_id, page.content)
            
            self.logger.info(f"Successfully updated Notion page: {page_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating Notion page {page_id}: {e}")
            return False
    
    async def _update_page_content(self, page_id: str, content: str):
        """Update page content by replacing all blocks."""
        try:
            # Get current page blocks
            blocks_url = f"{self.base_url}/blocks/{page_id}/children"
            response = requests.get(blocks_url, headers=self.headers)
            response.raise_for_status()
            
            blocks_data = response.json()
            existing_blocks = blocks_data.get('results', [])
            
            # Delete existing blocks
            for block in existing_blocks:
                block_id = block.get('id')
                if block_id:
                    delete_url = f"{self.base_url}/blocks/{block_id}"
                    requests.delete(delete_url, headers=self.headers)
            
            # Add new content blocks
            children = self._build_content_blocks(content)
            if children:
                append_url = f"{self.base_url}/blocks/{page_id}/children"
                append_payload = {"children": children}
                requests.patch(append_url, headers=self.headers, json=append_payload)
            
        except Exception as e:
            self.logger.error(f"Error updating page content: {e}")
    
    async def search_pages(self, query: str, database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for pages in Notion."""
        try:
            url = f"{self.base_url}/search"
            payload = {
                "query": query,
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }
            
            if database_id:
                payload["filter"] = {
                    "value": database_id,
                    "property": "parent"
                }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except Exception as e:
            self.logger.error(f"Error searching Notion pages: {e}")
            return []
    
    async def get_database_schema(self, database_id: str) -> Optional[Dict[str, Any]]:
        """Get database schema information."""
        try:
            url = f"{self.base_url}/databases/{database_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error getting database schema: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test Notion API connection."""
        try:
            url = f"{self.base_url}/users/me"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            self.logger.info("Notion API connection successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Notion API connection failed: {e}")
            return False
