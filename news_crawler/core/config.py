"""
Configuration management for the news crawler.
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class AIConfig(BaseModel):
    """AI provider configuration."""
    provider: str = Field(default="openai", description="AI provider (openai, anthropic)")
    model: str = Field(default="gpt-4", description="AI model to use")
    api_key: str = Field(..., description="API key for the AI provider")
    max_tokens: int = Field(default=4000, description="Maximum tokens for AI responses")
    temperature: float = Field(default=0.7, description="Temperature for AI responses")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default="sqlite:///crawler.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQLAlchemy echo")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum overflow connections")


class CrawlerConfig(BaseModel):
    """Crawler configuration."""
    user_agent: str = Field(default="NewsCrawler/1.0.0", description="User agent string")
    request_delay: float = Field(default=1.0, description="Delay between requests in seconds")
    max_concurrent_requests: int = Field(default=5, description="Maximum concurrent requests")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt")


class YouTubeConfig(BaseModel):
    """YouTube configuration."""
    api_key: Optional[str] = Field(default=None, description="YouTube API key")
    max_video_length: int = Field(default=3600, description="Maximum video length in seconds")
    transcript_language: str = Field(default="en", description="Preferred transcript language")


class StorageConfig(BaseModel):
    """Storage configuration."""
    path: str = Field(default="./data", description="Storage path")
    max_content_length: int = Field(default=1000000, description="Maximum content length")
    compression: bool = Field(default=True, description="Enable content compression")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    file: Optional[str] = Field(default=None, description="Log file path")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class DevBlogConfig(BaseModel):
    """Dev blog configuration."""
    url: str = Field(..., description="Blog URL")
    schedule: str = Field(default="0 9 * * *", description="Cron schedule")
    selectors: Dict[str, str] = Field(default_factory=dict, description="CSS selectors for content extraction")
    enabled: bool = Field(default=True, description="Whether this blog is enabled")


class YouTubeChannelConfig(BaseModel):
    """YouTube channel configuration."""
    url: str = Field(..., description="Channel URL")
    schedule: str = Field(default="0 12 * * *", description="Cron schedule")
    enabled: bool = Field(default=True, description="Whether this channel is enabled")


class YouTubeVideoConfig(BaseModel):
    """YouTube video configuration."""
    url: str = Field(..., description="Video URL")
    schedule: str = Field(default="0 18 * * *", description="Cron schedule")
    enabled: bool = Field(default=True, description="Whether this video is enabled")


class NotionConfig(BaseModel):
    """Notion integration configuration."""
    api_key: str = Field(..., description="Notion API key")


class Config(BaseModel):
    """Main configuration class."""
    ai: AIConfig
    database: DatabaseConfig
    crawler: CrawlerConfig
    youtube: YouTubeConfig
    storage: StorageConfig
    logging: LoggingConfig
    notion: NotionConfig
    dev_blogs: List[DevBlogConfig] = Field(default_factory=list)
    youtube_channels: List[YouTubeChannelConfig] = Field(default_factory=list)
    youtube_videos: List[YouTubeVideoConfig] = Field(default_factory=list)

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load environment variables
        load_dotenv()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace environment variables in YAML content
        def replace_env_vars(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            else:
                print(f"Warning: Environment variable {var_name} not found, keeping original value")
                return match.group(0)
        
        # Use the working regex pattern
        content = re.sub(r'\$\{([^}]+)\}', replace_env_vars, content)
        
        config_data = yaml.safe_load(content)
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()
        
        return cls(
            ai=AIConfig(
                provider=os.getenv("AI_PROVIDER", "openai"),
                model=os.getenv("AI_MODEL", "gpt-4"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                max_tokens=int(os.getenv("AI_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("AI_TEMPERATURE", "0.7"))
            ),
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///crawler.db"),
                echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
            ),
            crawler=CrawlerConfig(
                user_agent=os.getenv("USER_AGENT", "NewsCrawler/1.0.0"),
                request_delay=float(os.getenv("REQUEST_DELAY", "1.0")),
                max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
                timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
                retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
                respect_robots_txt=os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"
            ),
            youtube=YouTubeConfig(
                api_key=os.getenv("YOUTUBE_API_KEY"),
                max_video_length=int(os.getenv("YOUTUBE_MAX_LENGTH", "3600")),
                transcript_language=os.getenv("YOUTUBE_TRANSCRIPT_LANG", "en")
            ),
            storage=StorageConfig(
                path=os.getenv("STORAGE_PATH", "./data"),
                max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "1000000")),
                compression=os.getenv("ENABLE_COMPRESSION", "true").lower() == "true"
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                file=os.getenv("LOG_FILE"),
                format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
        )
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, indent=2)
