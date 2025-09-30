"""
Keyword-based content filtering.
"""

import re
import logging
from typing import List, Dict, Any
from news_crawler.filters.content_filter import KeywordFilter


class BackendKeywordFilter(KeywordFilter):
    """Specialized keyword filter for backend content."""
    
    def __init__(self, config: Dict[str, Any]):
        # Set up backend-specific keywords
        backend_config = {
            'required': [
                # Korean backend keywords
                '백엔드', '서버', 'API', '데이터베이스', '서버사이드',
                '자바', '파이썬', '스프링', '장고', '플라스크',
                '마이크로서비스', 'REST', 'GraphQL', 'gRPC',
                '도커', '쿠버네티스', 'AWS', 'Azure', 'GCP',
                'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
                'DevOps', 'CI/CD', '모니터링', '로깅',
                
                # English backend keywords
                'backend', 'server', 'api', 'database', 'server-side',
                'java', 'python', 'spring', 'django', 'flask',
                'microservices', 'rest', 'graphql', 'grpc',
                'docker', 'kubernetes', 'aws', 'azure', 'gcp',
                'mysql', 'postgresql', 'mongodb', 'redis',
                'devops', 'ci/cd', 'monitoring', 'logging'
            ],
            'excluded': [
                # Frontend keywords to exclude
                '프론트엔드', 'UI', 'UX', '디자인', 'CSS', 'HTML',
                '자바스크립트', '리액트', '뷰', '앵귤러',
                '버튼', '폼', '레이아웃', '반응형', '모바일',
                
                'frontend', 'ui', 'ux', 'design', 'css', 'html',
                'javascript', 'react', 'vue', 'angular',
                'button', 'form', 'layout', 'responsive', 'mobile'
            ],
            'case_sensitive': False,
            'match_all_required': False  # Match any required keyword
        }
        
        # Merge with provided config
        merged_config = {**backend_config, **config}
        super().__init__(merged_config)
        self.logger = logging.getLogger(__name__)
    
    def should_include(self, content) -> bool:
        """Check if content matches backend keyword criteria."""
        # Use parent class logic first
        if not super().should_include(content):
            return False
        
        # Additional backend-specific scoring
        content_text = f"{content.title} {content.content}".lower()
        
        # Score based on backend keyword density
        backend_score = self._calculate_backend_score(content_text)
        frontend_score = self._calculate_frontend_score(content_text)
        
        # Include if backend score is higher than frontend score
        return backend_score > frontend_score
    
    def _calculate_backend_score(self, content_text: str) -> int:
        """Calculate backend relevance score."""
        backend_keywords = [
            'backend', 'server', 'api', 'database', 'server-side',
            'java', 'python', 'spring', 'django', 'flask',
            'microservices', 'rest', 'graphql', 'grpc',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'mysql', 'postgresql', 'mongodb', 'redis',
            'devops', 'ci/cd', 'monitoring', 'logging',
            '백엔드', '서버', 'API', '데이터베이스', '서버사이드',
            '자바', '파이썬', '스프링', '장고', '플라스크',
            '마이크로서비스', 'REST', 'GraphQL', 'gRPC',
            '도커', '쿠버네티스', 'AWS', 'Azure', 'GCP',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
            'DevOps', 'CI/CD', '모니터링', '로깅'
        ]
        
        score = 0
        for keyword in backend_keywords:
            if keyword.lower() in content_text:
                score += 1
        
        return score
    
    def _calculate_frontend_score(self, content_text: str) -> int:
        """Calculate frontend relevance score."""
        frontend_keywords = [
            'frontend', 'ui', 'ux', 'design', 'css', 'html',
            'javascript', 'react', 'vue', 'angular',
            'button', 'form', 'layout', 'responsive', 'mobile',
            '프론트엔드', 'UI', 'UX', '디자인', 'CSS', 'HTML',
            '자바스크립트', '리액트', '뷰', '앵귤러',
            '버튼', '폼', '레이아웃', '반응형', '모바일'
        ]
        
        score = 0
        for keyword in frontend_keywords:
            if keyword.lower() in content_text:
                score += 1
        
        return score
