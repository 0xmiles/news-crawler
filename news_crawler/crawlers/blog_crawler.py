"""
Blog crawler for extracting content from development blogs.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime
import feedparser
import newspaper
from news_crawler.crawlers.base import BaseCrawler, CrawledContent


class BlogCrawler(BaseCrawler):
    """Crawler for development blogs."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Common selectors for different blog platforms
        self.default_selectors = {
            'title': ['h1', 'h2.title', '.post-title', '.entry-title', 'title'],
            'content': ['.post-content', '.entry-content', '.content', 'article', '.post-body'],
            'author': ['.author', '.byline', '.post-author', '[rel="author"]'],
            'date': ['.date', '.published', '.post-date', 'time', '[datetime]'],
            'tags': ['.tags a', '.categories a', '.post-tags a', '.tag']
        }
    
    async def crawl(self, url: str) -> List[CrawledContent]:
        """Crawl content from a blog URL."""
        self.logger.info(f"Starting blog crawl for {url}")
        
        try:
            # Try to find RSS/Atom feed first
            feed_content = await self._try_feed_crawl(url)
            if feed_content:
                return feed_content
            
            # Fallback to regular web crawling
            return await self._web_crawl(url)
            
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return []
    
    async def _try_feed_crawl(self, url: str) -> Optional[List[CrawledContent]]:
        """Try to crawl using RSS/Atom feed."""
        feed_urls = [
            urljoin(url, '/feed'),
            urljoin(url, '/rss'),
            urljoin(url, '/atom'),
            urljoin(url, '/feed.xml'),
            urljoin(url, '/rss.xml'),
            urljoin(url, '/atom.xml')
        ]
        
        for feed_url in feed_urls:
            try:
                self.logger.debug(f"Trying feed: {feed_url}")
                response = await self._make_request(feed_url)
                if not response:
                    continue
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                if feed.bozo == 0 and feed.entries:  # Valid feed with entries
                    self.logger.info(f"Found valid feed: {feed_url}")
                    return self._parse_feed_entries(feed, url)
                    
            except Exception as e:
                self.logger.debug(f"Feed {feed_url} failed: {e}")
                continue
        
        return None
    
    def _parse_feed_entries(self, feed: feedparser.FeedParserDict, base_url: str) -> List[CrawledContent]:
        """Parse RSS/Atom feed entries."""
        contents = []
        
        for entry in feed.entries[:10]:  # Limit to 10 most recent entries
            try:
                # Extract basic information
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # Extract content
                content = ''
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].value
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                
                # Extract author
                author = None
                if hasattr(entry, 'author'):
                    author = entry.author
                elif hasattr(entry, 'authors') and entry.authors:
                    author = entry.authors[0].get('name', '')
                
                # Extract published date
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_date = datetime(*entry.updated_parsed[:6])
                
                # Extract tags
                tags = []
                if hasattr(entry, 'tags') and entry.tags:
                    tags = [tag.term for tag in entry.tags]
                
                # Clean content
                content = self._clean_content(content)
                
                if title and content:
                    contents.append(CrawledContent(
                        url=link,
                        title=title,
                        content=content,
                        author=author,
                        published_date=published_date,
                        tags=tags,
                        metadata={'source': 'feed', 'feed_url': base_url}
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Error parsing feed entry: {e}")
                continue
        
        return contents
    
    async def _web_crawl(self, url: str) -> List[CrawledContent]:
        """Crawl blog content from web pages."""
        soup = await self._fetch_page(url)
        if not soup:
            return []
        
        # Try to find article links
        article_links = self._find_article_links(soup, url)
        
        contents = []
        for article_url in article_links[:5]:  # Limit to 5 articles
            try:
                article_content = await self._crawl_article(article_url)
                if article_content:
                    contents.append(article_content)
            except Exception as e:
                self.logger.warning(f"Error crawling article {article_url}: {e}")
                continue
        
        return contents
    
    def _find_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find article links on a blog page."""
        article_links = []
        
        # Common selectors for article links
        link_selectors = [
            'a[href*="/post/"]',
            'a[href*="/article/"]',
            'a[href*="/blog/"]',
            'a[href*="/entry/"]',
            '.post-title a',
            '.entry-title a',
            'article a',
            '.post a'
        ]
        
        for selector in link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    if self._is_valid_url(absolute_url) and absolute_url not in article_links:
                        article_links.append(absolute_url)
        
        return article_links
    
    async def _crawl_article(self, url: str) -> Optional[CrawledContent]:
        """Crawl a single article."""
        soup = await self._fetch_page(url)
        if not soup:
            return None
        
        # Extract title
        title = self._extract_title(soup)
        if not title:
            return None
        
        # Extract content
        content = self._extract_article_content(soup)
        if not content:
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
            metadata={'source': 'web'}
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title."""
        for selector in self.default_selectors['title']:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:  # Reasonable title length
                    return title
        
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return ""
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content."""
        # Try different content selectors
        for selector in self.default_selectors['content']:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator='\n', strip=True)
                if content and len(content) > 100:  # Reasonable content length
                    return self._clean_content(content)
        
        # Fallback: try to find the largest text block
        paragraphs = soup.find_all('p')
        if paragraphs:
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            if content and len(content) > 100:
                return self._clean_content(content)
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author."""
        for selector in self.default_selectors['author']:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True)
                if author and len(author) < 100:  # Reasonable author name length
                    return author
        
        return None
    
    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract published date."""
        for selector in self.default_selectors['date']:
            element = soup.select_one(selector)
            if element:
                # Try datetime attribute first
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
                        # Try common date formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%B %d, %Y', '%d %B %Y']:
                            try:
                                return datetime.strptime(date_text, fmt)
                            except ValueError:
                                continue
                    except Exception:
                        pass
        
        return None
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract article tags."""
        tags = []
        for selector in self.default_selectors['tags']:
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
        
        # Remove common unwanted elements
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
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Decode HTML entities
        import html
        content = html.unescape(content)
        
        return content.strip()
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains for this crawler."""
        return [
            'medium.com',
            'dev.to',
            'hashnode.com',
            'blogspot.com',
            'wordpress.com',
            'github.io',
            'netlify.app',
            'vercel.app'
        ]
