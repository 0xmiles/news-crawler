#!/usr/bin/env python3
"""
Example script for crawling maeil-mail.kr with pattern-based URLs.
This script demonstrates how to crawl the specific pattern mentioned:
https://www.maeil-mail.kr/question/50 (where only the number changes)
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from news_crawler.core.config import Config
from news_crawler.core.crawler import Crawler
from news_crawler.filters.keyword_filter import BackendKeywordFilter
from news_crawler.filters.category_filter import BackendCategoryFilter


async def crawl_maeil_mail_pattern():
    """Crawl maeil-mail.kr with pattern-based URLs."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Configuration for maeil-mail.kr pattern crawling
    config = {
        'ai': {
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key': 'your-openai-api-key-here',
            'max_tokens': 4000,
            'temperature': 0.7
        },
        'crawler': {
            'user_agent': 'NewsCrawler/1.0.0',
            'request_delay': 1.0,
            'max_concurrent_requests': 3,
            'timeout': 30,
            'retry_attempts': 3
        },
        'notion': {
            'api_key': 'your-notion-api-key-here'
        },
        'filters': {
            'keywords': {
                'enabled': True,
                'required': [
                    '백엔드', '서버', 'API', '데이터베이스', '자바', '스프링',
                    'backend', 'server', 'api', 'database', 'java', 'spring'
                ],
                'excluded': [
                    '프론트엔드', 'UI', 'UX', 'frontend', 'ui', 'ux'
                ],
                'case_sensitive': False,
                'match_all_required': False
            },
            'categories': {
                'enabled': True,
                'allowed': ['backend', 'database', 'api'],
                'excluded': ['frontend', 'design'],
                'category_keywords': {
                    'backend': [
                        '백엔드', '서버', 'API', '데이터베이스', '자바', '스프링',
                        'backend', 'server', 'api', 'database', 'java', 'spring'
                    ],
                    'database': [
                        '데이터베이스', 'database', 'mysql', 'postgresql', 'mongodb'
                    ],
                    'api': [
                        'API', 'api', 'rest', 'graphql', 'grpc'
                    ]
                }
            },
            'length': {
                'enabled': True,
                'min_length': 100,
                'max_length': 10000,
                'min_title_length': 10
            }
        },
        'pattern': {
            'max_pages': 20,
            'patterns': [
                {
                    'type': 'numeric_range',
                    'start': 1,
                    'end': 100,
                    'template': 'https://www.maeil-mail.kr/question/{number}'
                }
            ]
        }
    }
    
    try:
        # Initialize crawler
        crawler = Crawler(config)
        
        # Test connections
        logger.info("Testing connections...")
        connection_results = await crawler.test_connections()
        
        for service, status in connection_results.items():
            status_text = "✓ Connected" if status else "✗ Failed"
            logger.info(f"{service.title()}: {status_text}")
        
        if not connection_results.get('ai', False):
            logger.error("AI service connection failed. Please check your API key.")
            return
        
        # Crawl pattern URLs
        logger.info("Starting pattern crawl for maeil-mail.kr...")
        base_url = "https://www.maeil-mail.kr"
        
        contents = await crawler.crawl_pattern_urls(base_url, config['pattern'])
        
        if not contents:
            logger.warning("No content found or crawled.")
            return
        
        logger.info(f"Successfully crawled {len(contents)} items")
        
        # Display results
        for i, content in enumerate(contents, 1):
            logger.info(f"\n--- Item {i} ---")
            logger.info(f"Title: {content.title}")
            logger.info(f"URL: {content.url}")
            logger.info(f"Author: {content.author or 'Unknown'}")
            logger.info(f"Content Length: {len(content.content)}")
            logger.info(f"Tags: {', '.join(content.tags) if content.tags else 'None'}")
            
            # Show first 200 characters of content
            preview = content.content[:200] + "..." if len(content.content) > 200 else content.content
            logger.info(f"Content Preview: {preview}")
        
        # If Notion is configured, upload summaries
        if connection_results.get('notion', False):
            notion_db_id = input("Enter Notion Database ID (or press Enter to skip): ").strip()
            if notion_db_id:
                logger.info("Uploading summaries to Notion...")
                page_ids = await crawler.summarize_and_upload(contents, notion_db_id)
                logger.info(f"Successfully uploaded {len(page_ids)} items to Notion")
        
        # Generate summaries for display
        logger.info("\nGenerating summaries...")
        for i, content in enumerate(contents[:3], 1):  # Show first 3 summaries
            logger.info(f"\n--- Summary {i} ---")
            logger.info(f"Title: {content.title}")
            
            # Get summary
            summary = await crawler.summarizer.summarize(content.content)
            logger.info(f"Summary: {summary}")
            
            # Get key points
            key_points = await crawler.summarizer.extract_key_points(content.content)
            if key_points:
                logger.info("Key Points:")
                for j, point in enumerate(key_points, 1):
                    logger.info(f"  {j}. {point}")
    
    except Exception as e:
        logger.error(f"Error in crawling process: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(crawl_maeil_mail_pattern())
