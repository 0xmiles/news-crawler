"""Input validation utilities."""

import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class KeywordInput(BaseModel):
    """Validated keyword input."""
    keywords: str = Field(..., min_length=1, max_length=500)

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        """Validate keyword string.

        Args:
            v: Keyword string

        Returns:
            Validated keyword string

        Raises:
            ValueError: If validation fails
        """
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())

        # Check for minimum length
        if len(cleaned) < 3:
            raise ValueError("Keywords must be at least 3 characters long")

        # Check for valid characters (alphanumeric, spaces, common punctuation)
        if not re.match(r'^[a-zA-Z0-9\s\-_.,:()]+$', cleaned):
            raise ValueError("Keywords contain invalid characters")

        return cleaned


class BlogContent(BaseModel):
    """Validated blog content."""
    title: str = Field(..., min_length=10, max_length=200)
    content: str = Field(..., min_length=100)
    sections: Optional[List[str]] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate blog title.

        Args:
            v: Title string

        Returns:
            Validated title

        Raises:
            ValueError: If validation fails
        """
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())

        if len(cleaned) < 10:
            raise ValueError("Title must be at least 10 characters long")

        if len(cleaned) > 200:
            raise ValueError("Title must not exceed 200 characters")

        return cleaned

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate blog content.

        Args:
            v: Content string

        Returns:
            Validated content

        Raises:
            ValueError: If validation fails
        """
        if len(v.strip()) < 100:
            raise ValueError("Content must be at least 100 characters long")

        return v


class SearchResult(BaseModel):
    """Validated search result."""
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    snippet: str = Field(default="")
    content: Optional[str] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL.

        Args:
            v: URL string

        Returns:
            Validated URL

        Raises:
            ValueError: If validation fails
        """
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(v):
            raise ValueError(f"Invalid URL: {v}")

        return v


def validate_file_path(filepath: str, must_exist: bool = False) -> str:
    """Validate file path.

    Args:
        filepath: Path to validate
        must_exist: Whether file must exist

    Returns:
        Validated file path

    Raises:
        ValueError: If validation fails
    """
    from pathlib import Path

    path = Path(filepath)

    # Check for path traversal attempts
    try:
        path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid file path: {e}")

    # Check if file must exist
    if must_exist and not path.exists():
        raise ValueError(f"File does not exist: {filepath}")

    return str(path)


def validate_tone_profile(profile: dict) -> bool:
    """Validate tone profile structure.

    Args:
        profile: Tone profile dictionary

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    required_keys = {"characteristics", "vocabulary", "patterns", "style"}

    if not all(key in profile for key in required_keys):
        missing = required_keys - set(profile.keys())
        raise ValueError(f"Tone profile missing required keys: {missing}")

    # Validate that values are non-empty
    for key in required_keys:
        if not profile[key]:
            raise ValueError(f"Tone profile '{key}' cannot be empty")

    return True
