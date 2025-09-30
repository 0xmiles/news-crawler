"""
Content filtering system for crawled content.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from abc import ABC, abstractmethod
from news_crawler.crawlers.base import CrawledContent


class BaseContentFilter(ABC):
    """Base class for content filters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content should be included."""
        pass
    
    @abstractmethod
    def get_filter_name(self) -> str:
        """Get filter name for logging."""
        pass


class ContentFilter:
    """Main content filter that combines multiple filters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.filters = self._initialize_filters()
    
    def _initialize_filters(self) -> List[BaseContentFilter]:
        """Initialize all configured filters."""
        filters = []
        
        # Keyword filter
        if self.config.get('keywords', {}).get('enabled', False):
            filters.append(KeywordFilter(self.config.get('keywords', {})))
        
        # Category filter
        if self.config.get('categories', {}).get('enabled', False):
            filters.append(CategoryFilter(self.config.get('categories', {})))
        
        # Length filter
        if self.config.get('length', {}).get('enabled', False):
            filters.append(LengthFilter(self.config.get('length', {})))
        
        # Quality filter
        if self.config.get('quality', {}).get('enabled', False):
            filters.append(QualityFilter(self.config.get('quality', {})))
        
        return filters
    
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content should be included based on all filters."""
        for filter_obj in self.filters:
            if not filter_obj.should_include(content):
                self.logger.debug(f"Content filtered out by {filter_obj.get_filter_name()}: {content.url}")
                return False
        
        return True
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get statistics about filter performance."""
        return {
            'total_filters': len(self.filters),
            'filter_names': [f.get_filter_name() for f in self.filters]
        }


class KeywordFilter(BaseContentFilter):
    """Filter content based on keywords."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.required_keywords = config.get('required', [])
        self.excluded_keywords = config.get('excluded', [])
        self.case_sensitive = config.get('case_sensitive', False)
        self.match_all_required = config.get('match_all_required', False)
    
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content matches keyword criteria."""
        content_text = f"{content.title} {content.content}"
        
        if not self.case_sensitive:
            content_text = content_text.lower()
            required_keywords = [kw.lower() for kw in self.required_keywords]
            excluded_keywords = [kw.lower() for kw in self.excluded_keywords]
        else:
            required_keywords = self.required_keywords
            excluded_keywords = self.excluded_keywords
        
        # Check excluded keywords first
        for keyword in excluded_keywords:
            if keyword in content_text:
                return False
        
        # Check required keywords
        if self.required_keywords:
            if self.match_all_required:
                # Must match ALL required keywords
                return all(keyword in content_text for keyword in required_keywords)
            else:
                # Must match at least ONE required keyword
                return any(keyword in content_text for keyword in required_keywords)
        
        return True
    
    def get_filter_name(self) -> str:
        return "KeywordFilter"


class CategoryFilter(BaseContentFilter):
    """Filter content based on categories."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.allowed_categories = config.get('allowed', [])
        self.excluded_categories = config.get('excluded', [])
        self.category_keywords = config.get('category_keywords', {})
    
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content matches category criteria."""
        # Check if content has any excluded categories
        for category in self.excluded_categories:
            if self._content_has_category(content, category):
                return False
        
        # If allowed categories are specified, check if content matches any
        if self.allowed_categories:
            return any(self._content_has_category(content, category) for category in self.allowed_categories)
        
        return True
    
    def _content_has_category(self, content: CrawledContent, category: str) -> bool:
        """Check if content belongs to a specific category."""
        content_text = f"{content.title} {content.content}".lower()
        
        # Check category keywords
        if category in self.category_keywords:
            keywords = self.category_keywords[category]
            return any(keyword.lower() in content_text for keyword in keywords)
        
        # Check tags
        if content.tags:
            return category.lower() in [tag.lower() for tag in content.tags]
        
        return False
    
    def get_filter_name(self) -> str:
        return "CategoryFilter"


class LengthFilter(BaseContentFilter):
    """Filter content based on length criteria."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_length = config.get('min_length', 0)
        self.max_length = config.get('max_length', float('inf'))
        self.min_title_length = config.get('min_title_length', 0)
        self.max_title_length = config.get('max_title_length', float('inf'))
    
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content meets length criteria."""
        content_length = len(content.content)
        title_length = len(content.title)
        
        # Check content length
        if content_length < self.min_length or content_length > self.max_length:
            return False
        
        # Check title length
        if title_length < self.min_title_length or title_length > self.max_title_length:
            return False
        
        return True
    
    def get_filter_name(self) -> str:
        return "LengthFilter"


class QualityFilter(BaseContentFilter):
    """Filter content based on quality metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_word_count = config.get('min_word_count', 0)
        self.max_word_count = config.get('max_word_count', float('inf'))
        self.min_sentence_count = config.get('min_sentence_count', 0)
        self.require_proper_sentences = config.get('require_proper_sentences', True)
        self.min_paragraph_count = config.get('min_paragraph_count', 0)
    
    def should_include(self, content: CrawledContent) -> bool:
        """Check if content meets quality criteria."""
        # Count words
        word_count = len(content.content.split())
        if word_count < self.min_word_count or word_count > self.max_word_count:
            return False
        
        # Count sentences
        sentences = re.split(r'[.!?]+', content.content)
        sentence_count = len([s for s in sentences if s.strip()])
        if sentence_count < self.min_sentence_count:
            return False
        
        # Check for proper sentences
        if self.require_proper_sentences:
            proper_sentences = 0
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 10:  # Reasonable sentence length
                    proper_sentences += 1
            
            if proper_sentences < self.min_sentence_count:
                return False
        
        # Count paragraphs
        paragraphs = [p for p in content.content.split('\n\n') if p.strip()]
        if len(paragraphs) < self.min_paragraph_count:
            return False
        
        return True
    
    def get_filter_name(self) -> str:
        return "QualityFilter"
