"""
Category-based content filtering.
"""

import logging
from typing import List, Dict, Any
from news_crawler.filters.content_filter import CategoryFilter


class BackendCategoryFilter(CategoryFilter):
    """Specialized filter for backend-related content."""
    
    def __init__(self, config: Dict[str, Any]):
        # Set up backend-specific category keywords
        backend_config = {
            'allowed': ['backend', 'server', 'api', 'database', 'devops'],
            'excluded': ['frontend', 'ui', 'ux', 'design'],
            'category_keywords': {
                'backend': [
                    '백엔드', '서버', 'API', '데이터베이스', '서버사이드',
                    'backend', 'server', 'database', 'api', 'server-side',
                    'spring', 'django', 'flask', 'express', 'node.js',
                    'java', 'python', 'go', 'rust', 'c#', 'php',
                    'mysql', 'postgresql', 'mongodb', 'redis',
                    'docker', 'kubernetes', 'aws', 'azure', 'gcp',
                    'microservices', 'rest', 'graphql', 'grpc'
                ],
                'database': [
                    '데이터베이스', 'database', 'db', 'sql', 'nosql',
                    'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                    'orm', 'jpa', 'hibernate', 'sequelize', 'prisma'
                ],
                'api': [
                    'API', 'api', 'rest', 'graphql', 'grpc', 'endpoint',
                    'swagger', 'openapi', 'postman', 'curl'
                ],
                'devops': [
                    'devops', 'deployment', 'ci/cd', 'docker', 'kubernetes',
                    'aws', 'azure', 'gcp', 'jenkins', 'github actions',
                    'terraform', 'ansible', 'monitoring', 'logging'
                ]
            }
        }
        
        # Merge with provided config
        merged_config = {**backend_config, **config}
        super().__init__(merged_config)
        self.logger = logging.getLogger(__name__)
    
    def should_include(self, content) -> bool:
        """Check if content is backend-related."""
        # First check if it's explicitly excluded
        if not super().should_include(content):
            return False
        
        # Additional backend-specific checks
        content_text = f"{content.title} {content.content}".lower()
        
        # Check for backend-related patterns
        backend_patterns = [
            r'\b(backend|server|api|database)\b',
            r'\b(java|python|go|rust|c#|php)\b',
            r'\b(spring|django|flask|express)\b',
            r'\b(mysql|postgresql|mongodb|redis)\b',
            r'\b(docker|kubernetes|aws|azure|gcp)\b',
            r'\b(microservices|rest|graphql|grpc)\b'
        ]
        
        has_backend_pattern = any(
            re.search(pattern, content_text, re.IGNORECASE) 
            for pattern in backend_patterns
        )
        
        if not has_backend_pattern:
            return False
        
        # Check for frontend-related content to exclude
        frontend_patterns = [
            r'\b(frontend|ui|ux|design|css|html|javascript|react|vue|angular)\b',
            r'\b(button|form|layout|responsive|mobile)\b'
        ]
        
        has_frontend_pattern = any(
            re.search(pattern, content_text, re.IGNORECASE) 
            for pattern in frontend_patterns
        )
        
        if has_frontend_pattern:
            # If it has both backend and frontend patterns, 
            # check which is more prominent
            backend_score = sum(1 for pattern in backend_patterns 
                              if re.search(pattern, content_text, re.IGNORECASE))
            frontend_score = sum(1 for pattern in frontend_patterns 
                              if re.search(pattern, content_text, re.IGNORECASE))
            
            return backend_score > frontend_score
        
        return True
