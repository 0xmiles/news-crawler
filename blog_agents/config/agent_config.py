"""Configuration management for blog agents system."""

import os
from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AIConfig(BaseModel):
    """AI provider configuration."""
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    api_key: str
    max_tokens: int = 4000
    temperature: float = 0.7


class SearchConfig(BaseModel):
    """Search provider configuration."""
    provider: Literal["google", "bing"] = "google"
    api_key: str
    search_engine_id: Optional[str] = None  # For Google
    max_results: int = 10


class PostSearcherConfig(BaseModel):
    """PostSearcher agent configuration."""
    enabled: bool = True
    max_articles: int = 3
    min_content_length: int = 500


class BlogPlannerConfig(BaseModel):
    """BlogPlanner agent configuration."""
    enabled: bool = True
    min_sections: int = 3
    max_sections: int = 7


class BlogWriterConfig(BaseModel):
    """BlogWriter agent configuration."""
    enabled: bool = True
    section_word_target: int = 300
    apply_tone_analysis: bool = True


class BlogAgentsConfig(BaseModel):
    """Blog agents system configuration."""
    max_search_results: int = 3
    target_blog_length: int = 1500
    output_dir: str = "outputs"
    reference_file: str = "references/reference.md"
    max_retries: int = 3
    timeout: int = 120

    post_searcher: PostSearcherConfig = Field(default_factory=PostSearcherConfig)
    blog_planner: BlogPlannerConfig = Field(default_factory=BlogPlannerConfig)
    blog_writer: BlogWriterConfig = Field(default_factory=BlogWriterConfig)


class Config(BaseModel):
    """Main configuration model."""
    ai: AIConfig
    search: SearchConfig
    blog_agents: BlogAgentsConfig = Field(default_factory=BlogAgentsConfig)

    @property
    def output_path(self) -> Path:
        """Get output directory path."""
        return Path(self.blog_agents.output_dir)

    @property
    def reference_path(self) -> Path:
        """Get reference file path."""
        return Path(self.blog_agents.reference_file)


def substitute_env_vars(data: dict) -> dict:
    """Recursively substitute environment variables in configuration.

    Replaces ${VAR_NAME} with the value of environment variable VAR_NAME.
    """
    if isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Replace ${VAR_NAME} with environment variable
        if data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            return os.getenv(var_name, data)
        return data
    else:
        return data


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML
    with open(config_file, 'r') as f:
        raw_config = yaml.safe_load(f)

    # Substitute environment variables
    config_data = substitute_env_vars(raw_config)

    # Parse with Pydantic
    try:
        config = Config(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")

    return config


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get global configuration instance (singleton pattern).

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration object
    """
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None
