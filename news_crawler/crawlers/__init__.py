"""
Web crawlers for different content types.
"""

from news_crawler.crawlers.blog_crawler import BlogCrawler
from news_crawler.crawlers.youtube_crawler import YouTubeCrawler

__all__ = ["BlogCrawler", "YouTubeCrawler"]
