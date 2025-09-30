"""
Base crawler class with common functionality.
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import random
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CrawledContent:
    """Represents crawled content."""
    url: str
    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class BaseCrawler(ABC):
    """Base crawler class with common functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
        self._last_request_time = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session with proper configuration."""
        timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
        headers = {
            'User-Agent': self.config.get('user_agent', 'NewsCrawler/1.0.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        connector = aiohttp.TCPConnector(
            limit=self.config.get('max_concurrent_requests', 5),
            limit_per_host=2,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector
        )
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def _respect_rate_limit(self):
        """Respect rate limiting between requests."""
        request_delay = self.config.get('request_delay', 1.0)
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < request_delay:
            sleep_time = request_delay - time_since_last_request
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    async def _make_request(self, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Make HTTP request with retry logic."""
        await self._respect_rate_limit()
        
        retry_attempts = self.config.get('retry_attempts', 3)
        
        for attempt in range(retry_attempts):
            try:
                self.logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                response = await self.session.get(url, **kwargs)
                
                if response.status == 200:
                    return response
                elif response.status == 429:  # Rate limited
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    self.logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.warning(f"HTTP {response.status} for {url}")
                    if attempt == retry_attempts - 1:
                        return None
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
                if attempt == retry_attempts - 1:
                    return None
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                self.logger.error(f"Error requesting {url}: {e}")
                if attempt == retry_attempts - 1:
                    return None
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        response = await self._make_request(url)
        if not response:
            return None
        
        try:
            content = await response.text()
            return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error parsing content from {url}: {e}")
            return None
    
    def _extract_text(self, element, selector: str = None) -> str:
        """Extract text from BeautifulSoup element."""
        if not element:
            return ""
        
        if selector:
            target = element.select_one(selector)
            if target:
                return target.get_text(strip=True)
        else:
            return element.get_text(strip=True)
        
        return ""
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize links from a page."""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            parsed_url = urlparse(absolute_url)
            
            # Only include HTTP/HTTPS links from the same domain
            if parsed_url.scheme in ['http', 'https']:
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    @abstractmethod
    async def crawl(self, url: str) -> List[CrawledContent]:
        """Crawl content from the given URL."""
        pass
    
    @abstractmethod
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains for this crawler."""
        pass
