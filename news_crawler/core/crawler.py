"""
Main crawler orchestrator that coordinates all crawling activities.
"""

import asyncio
import logging
import os
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from urllib.parse import urlparse

from news_crawler.crawlers.blog_crawler import BlogCrawler
from news_crawler.crawlers.youtube_crawler import YouTubeCrawler
from news_crawler.crawlers.pattern_crawler import PatternCrawler
from news_crawler.ai.summarizer import Summarizer
from news_crawler.integrations.notion_client import NotionClient, NotionPage
from news_crawler.integrations.notion_mcp_client import NotionMCPClient
from news_crawler.filters.content_filter import ContentFilter
from news_crawler.crawlers.base import CrawledContent


class Crawler:
    """Main crawler orchestrator."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.blog_crawler = BlogCrawler(config.get('crawler', {}))
        self.youtube_crawler = YouTubeCrawler(config.get('youtube', {}))
        self.pattern_crawler = PatternCrawler(config.get('pattern', {}))
        self.summarizer = Summarizer(config.get('ai', {}))
        self.notion_client = NotionClient(config.get('notion', {}))
        # Pass the api_key directly to NotionMCPClient
        notion_config = config.get('notion', {})
        self.logger.info(f"Notion config: {notion_config}")
        self.logger.info(f"Notion API key: {notion_config.get('api_key', 'NOT_FOUND')}")
        
        self.notion_mcp_client = NotionMCPClient({'api_key': notion_config.get('api_key')})
        self.content_filter = ContentFilter(config.get('filters', {}))
    
    async def crawl_url(self, url: str, content_type: str = "auto") -> List[CrawledContent]:
        """Crawl a single URL."""
        self.logger.info(f"Starting crawl for {url}")
        
        try:
            # Determine content type if auto
            if content_type == "auto":
                content_type = self._detect_content_type(url)
            
            # Crawl based on content type
            if content_type == "blog":
                contents = await self._crawl_blog(url)
            elif content_type == "youtube":
                contents = await self._crawl_youtube(url)
            elif content_type == "pattern":
                contents = await self._crawl_pattern(url)
            else:
                self.logger.error(f"Unknown content type: {content_type}")
                return []
            
            # Apply content filtering
            filtered_contents = []
            for content in contents:
                if self.content_filter.should_include(content):
                    filtered_contents.append(content)
                else:
                    self.logger.debug(f"Content filtered out: {content.url}")
            
            self.logger.info(f"Crawled {len(filtered_contents)} items from {url}")
            return filtered_contents
            
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return []
    
    async def crawl_pattern_urls(self, base_url: str, pattern_config: Dict[str, Any]) -> List[CrawledContent]:
        """Crawl URLs based on patterns."""
        self.logger.info(f"Starting pattern crawl for {base_url}")
        
        try:
            # Update pattern crawler config
            self.pattern_crawler.config.update(pattern_config)
            
            # Crawl pattern URLs
            contents = await self.pattern_crawler.crawl(base_url)
            
            # Apply content filtering
            filtered_contents = []
            for content in contents:
                if self.content_filter.should_include(content):
                    filtered_contents.append(content)
                else:
                    self.logger.debug(f"Content filtered out: {content.url}")
            
            self.logger.info(f"Pattern crawl completed: {len(filtered_contents)} items")
            return filtered_contents
            
        except Exception as e:
            self.logger.error(f"Error in pattern crawl: {e}")
            return []
    
    async def summarize_and_upload(self, contents: List[CrawledContent], 
                                 notion_database_id: str) -> List[str]:
        """Summarize contents and upload to Notion."""
        self.logger.info(f"Starting summarization and upload for {len(contents)} items")
        
        uploaded_page_ids = []
        
        for content in contents:
            try:
                # Summarize content
                summary = await self.summarizer.summarize(content.content)
                if not summary:
                    self.logger.warning(f"Failed to summarize content: {content.url}")
                    continue
                
                # Extract key points
                key_points = await self.summarizer.extract_key_points(content.content)
                
                # Generate title if needed
                title = content.title
                if not title or title == "Untitled":
                    title = await self.summarizer.generate_title(content.content)
                
                # Create Notion page
                notion_page = NotionPage(
                    title=title,
                    content=f"{summary}\n\n## Key Points\n" + "\n".join([f"- {point}" for point in key_points]),
                    url=content.url,
                    tags=content.tags + ["백엔드", "개발"] if content.tags else ["백엔드", "개발"],
                    author=content.author,
                    published_date=content.published_date,
                    metadata={
                        **content.metadata,
                        'original_length': len(content.content),
                        'summary_length': len(summary),
                        'key_points_count': len(key_points)
                    }
                )
                
                # Upload to Notion
                page_id = await self.notion_client.create_page(notion_page, notion_database_id)
                if page_id:
                    uploaded_page_ids.append(page_id)
                    self.logger.info(f"Successfully uploaded to Notion: {page_id}")
                else:
                    self.logger.error(f"Failed to upload to Notion: {content.url}")
                
            except Exception as e:
                self.logger.error(f"Error processing content {content.url}: {e}")
                continue
        
        self.logger.info(f"Successfully uploaded {len(uploaded_page_ids)} items to Notion")
        return uploaded_page_ids
    
    async def add_summary_to_notion_page(self, page_url: str, contents: List[CrawledContent]) -> List[bool]:
        """Add summaries to a specific Notion page using MCP."""
        self.logger.info(f"Adding {len(contents)} summaries to Notion page: {page_url}")
        
        results = []
        
        for content in contents:
            try:
                # Summarize content
                summary = await self.summarizer.summarize(content.content)
                if not summary:
                    self.logger.warning(f"Failed to summarize content: {content.url}")
                    results.append(False)
                    continue
                
                # Extract key points
                key_points = await self.summarizer.extract_key_points(content.content)
                
                # Prepare summary data
                summary_data = {
                    'title': content.title,
                    'summary': summary,
                    'key_points': key_points,
                    'url': content.url,
                    'author': content.author,
                    'published_date': content.published_date.isoformat() if content.published_date else None
                }
                
                # Add to Notion page
                success = await self.notion_mcp_client.add_summary_to_page(page_url, summary_data)
                results.append(success)
                
                if success:
                    self.logger.info(f"Successfully added summary to page: {content.title}")
                else:
                    self.logger.error(f"Failed to add summary to page: {content.title}")
                
            except Exception as e:
                self.logger.error(f"Error processing content {content.url}: {e}")
                results.append(False)
        
        successful_count = sum(results)
        self.logger.info(f"Successfully added {successful_count}/{len(contents)} summaries to Notion page")
        return results
    
    async def _crawl_blog(self, url: str) -> List[CrawledContent]:
        """Crawl blog content."""
        async with self.blog_crawler:
            return await self.blog_crawler.crawl(url)
    
    async def _crawl_youtube(self, url: str) -> List[CrawledContent]:
        """Crawl YouTube content."""
        async with self.youtube_crawler:
            return await self.youtube_crawler.crawl(url)
    
    async def _crawl_pattern(self, url: str) -> List[CrawledContent]:
        """Crawl pattern-based content."""
        async with self.pattern_crawler:
            return await self.pattern_crawler.crawl(url)
    
    def _detect_content_type(self, url: str) -> str:
        """Detect content type from URL."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # YouTube detection
        if any(yt_domain in domain for yt_domain in ['youtube.com', 'youtu.be']):
            return "youtube"
        
        # For single URLs, always use blog crawler
        # Pattern detection is only for batch crawling
        return "blog"
    
    async def test_connections(self) -> Dict[str, bool]:
        """Test all service connections."""
        results = {}
        
        # Test Notion connection
        try:
            results['notion'] = self.notion_client.test_connection()
        except Exception as e:
            self.logger.error(f"Notion connection test failed: {e}")
            results['notion'] = False
        
        # Test AI services
        try:
            test_content = "This is a test content for AI services."
            summary = await self.summarizer.summarize(test_content)
            results['ai'] = bool(summary)
        except Exception as e:
            self.logger.error(f"AI service test failed: {e}")
            results['ai'] = False
        
        return results
    
    def get_crawler_stats(self) -> Dict[str, Any]:
        """Get crawler statistics."""
        return {
            'content_filter': self.content_filter.get_filter_stats(),
            'supported_domains': {
                'blog': self.blog_crawler.get_supported_domains(),
                'youtube': self.youtube_crawler.get_supported_domains(),
                'pattern': self.pattern_crawler.get_supported_domains()
            }
        }
