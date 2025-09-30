"""
Pattern-based crawler for URLs with specific patterns and content filtering.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime
import asyncio
from news_crawler.crawlers.base import BaseCrawler, CrawledContent


class PatternCrawler(BaseCrawler):
    """Crawler for pattern-based URLs with content filtering."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Pattern configuration
        self.patterns = config.get('patterns', [])
        self.content_filters = config.get('content_filters', {})
        self.required_keywords = config.get('required_keywords', [])
        self.excluded_keywords = config.get('excluded_keywords', [])
        self.max_pages = config.get('max_pages', 10)
        self.visited_urls: Set[str] = set()
    
    async def crawl(self, base_url: str) -> List[CrawledContent]:
        """Crawl content from pattern-based URLs."""
        self.logger.info(f"Starting pattern crawl for {base_url}")
        
        try:
            # Generate URLs based on patterns
            urls_to_crawl = await self._generate_urls(base_url)
            self.logger.info(f"Generated {len(urls_to_crawl)} URLs to crawl")
            
            # Crawl each URL
            contents = []
            for url in urls_to_crawl[:self.max_pages]:
                try:
                    content = await self._crawl_single_url(url)
                    if content:
                        # Apply content filtering
                        if self._should_include_content(content):
                            contents.append(content)
                        else:
                            self.logger.debug(f"Content filtered out: {url}")
                    
                    # Respect rate limiting
                    await asyncio.sleep(self.config.get('request_delay', 1.0))
                    
                except Exception as e:
                    self.logger.warning(f"Error crawling {url}: {e}")
                    continue
            
            self.logger.info(f"Successfully crawled {len(contents)} pages")
            return contents
            
        except Exception as e:
            self.logger.error(f"Error in pattern crawl: {e}")
            return []
    
    async def _generate_urls(self, base_url: str) -> List[str]:
        """Generate URLs based on patterns."""
        urls = []
        
        for pattern in self.patterns:
            if pattern.get('type') == 'numeric_range':
                urls.extend(self._generate_numeric_range_urls(base_url, pattern))
            elif pattern.get('type') == 'list':
                urls.extend(self._generate_list_urls(base_url, pattern))
            elif pattern.get('type') == 'regex':
                urls.extend(self._generate_regex_urls(base_url, pattern))
        
        # Remove duplicates and already visited URLs
        unique_urls = []
        for url in urls:
            if url not in self.visited_urls and url not in unique_urls:
                unique_urls.append(url)
        
        return unique_urls
    
    def _generate_numeric_range_urls(self, base_url: str, pattern: Dict[str, Any]) -> List[str]:
        """Generate URLs with numeric ranges."""
        urls = []
        
        start = pattern.get('start', 1)
        end = pattern.get('end', 100)
        step = pattern.get('step', 1)
        template = pattern.get('template', '{base_url}/{number}')
        
        for num in range(start, end + 1, step):
            url = template.format(base_url=base_url, number=num)
            urls.append(url)
        
        return urls
    
    def _generate_list_urls(self, base_url: str, pattern: Dict[str, Any]) -> List[str]:
        """Generate URLs from a list of values."""
        urls = []
        values = pattern.get('values', [])
        template = pattern.get('template', '{base_url}/{value}')
        
        for value in values:
            url = template.format(base_url=base_url, value=value)
            urls.append(url)
        
        return urls
    
    def _generate_regex_urls(self, base_url: str, pattern: Dict[str, Any]) -> List[str]:
        """Generate URLs using regex patterns."""
        urls = []
        regex_pattern = pattern.get('pattern', '')
        template = pattern.get('template', '{base_url}/{match}')
        
        # This would require more complex logic to generate URLs from regex
        # For now, we'll return empty list
        self.logger.warning("Regex URL generation not fully implemented")
        
        return urls
    
    async def _crawl_single_url(self, url: str) -> Optional[CrawledContent]:
        """Crawl a single URL."""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        soup = await self._fetch_page(url)
        if not soup:
            return None
        
        # Extract content
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        
        if not title or not content:
            return None
        
        # Extract metadata
        author = self._extract_author(soup)
        published_date = self._extract_published_date(soup)
        tags = self._extract_tags(soup)
        
        return CrawledContent(
            url=url,
            title=title,
            content=content,
            author=author,
            published_date=published_date,
            tags=tags,
            metadata={
                'source': 'pattern_crawl',
                'crawled_at': datetime.now().isoformat()
            }
        )
    
    def _extract_title(self, soup) -> str:
        """Extract page title."""
        title_selectors = [
            'h1', 'h2.title', '.post-title', '.entry-title', 
            'title', '.article-title', '.content-title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 5:
                    return title
        
        return ""
    
    def _extract_content(self, soup) -> str:
        """Extract main content."""
        content_selectors = [
            '.post-content', '.entry-content', '.content', 
            'article', '.post-body', '.article-content',
            'main', '.main-content'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator='\n', strip=True)
                if content and len(content) > 100:
                    return self._clean_content(content)
        
        # Fallback: get all paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            if content and len(content) > 100:
                return self._clean_content(content)
        
        return ""
    
    def _extract_author(self, soup) -> Optional[str]:
        """Extract author information."""
        author_selectors = [
            '.author', '.byline', '.post-author', '[rel="author"]',
            '.writer', '.contributor', '.user'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True)
                if author and len(author) < 100:
                    return author
        
        return None
    
    def _extract_published_date(self, soup) -> Optional[datetime]:
        """Extract published date."""
        date_selectors = [
            '.date', '.published', '.post-date', 'time', '[datetime]',
            '.publish-date', '.article-date', '.created-date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                # Try datetime attribute
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    try:
                        return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                # Try text content
                date_text = element.get_text(strip=True)
                if date_text:
                    try:
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%B %d, %Y', '%d %B %Y']:
                            try:
                                return datetime.strptime(date_text, fmt)
                            except ValueError:
                                continue
                    except Exception:
                        pass
        
        return None
    
    def _extract_tags(self, soup) -> List[str]:
        """Extract tags/categories."""
        tags = []
        tag_selectors = [
            '.tags a', '.categories a', '.post-tags a', '.tag',
            '.category', '.label', '.topic'
        ]
        
        for selector in tag_selectors:
            elements = soup.select(selector)
            for element in elements:
                tag = element.get_text(strip=True)
                if tag and tag not in tags:
                    tags.append(tag)
        
        return tags
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove unwanted patterns
        unwanted_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<style[^>]*>.*?</style>',
            r'<nav[^>]*>.*?</nav>',
            r'<footer[^>]*>.*?</footer>',
            r'<aside[^>]*>.*?</aside>',
            r'<header[^>]*>.*?</header>'
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        return content.strip()
    
    def _should_include_content(self, content: CrawledContent) -> bool:
        """Check if content should be included based on filters."""
        # Check required keywords
        if self.required_keywords:
            content_text = f"{content.title} {content.content}".lower()
            if not any(keyword.lower() in content_text for keyword in self.required_keywords):
                return False
        
        # Check excluded keywords
        if self.excluded_keywords:
            content_text = f"{content.title} {content.content}".lower()
            if any(keyword.lower() in content_text for keyword in self.excluded_keywords):
                return False
        
        # Check content length
        min_length = self.content_filters.get('min_length', 0)
        if len(content.content) < min_length:
            return False
        
        # Check title length
        min_title_length = self.content_filters.get('min_title_length', 0)
        if len(content.title) < min_title_length:
            return False
        
        # Check for specific content patterns
        content_patterns = self.content_filters.get('content_patterns', [])
        if content_patterns:
            content_text = f"{content.title} {content.content}".lower()
            if not any(re.search(pattern, content_text, re.IGNORECASE) for pattern in content_patterns):
                return False
        
        return True
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains for this crawler."""
        return []  # Pattern crawler works with any domain
