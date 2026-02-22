"""ToneLearner skill for analyzing and applying writing tone."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from anthropic import Anthropic
from blog_agents.config.agent_config import Config
from blog_agents.utils.file_manager import read_text_sync
from blog_agents.utils.validators import validate_tone_profile

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(".cache/tone_profiles")


class ToneLearner:
    """Skill for learning and applying writing tone from reference documents."""

    def __init__(self, config: Config):
        """Initialize ToneLearner.

        Args:
            config: System configuration
        """
        self.config = config
        self.client = Anthropic(api_key=config.ai.api_key)
        self.model = config.ai.model

        # In-memory cache for the current session
        self._tone_profile: Optional[Dict[str, Any]] = None
        self._reference_file_hash: Optional[str] = None

    @staticmethod
    def _log_cache_usage(usage: Any) -> None:
        """Log prompt cache hit/miss statistics from an API response.

        Args:
            usage: The usage object returned by the Anthropic API.
        """
        created = getattr(usage, "cache_creation_input_tokens", 0) or 0
        read = getattr(usage, "cache_read_input_tokens", 0) or 0
        regular = getattr(usage, "input_tokens", 0) or 0
        if created or read:
            logger.debug(
                "Prompt cache – write: %d tok, read: %d tok, uncached: %d tok",
                created,
                read,
                regular,
            )

    @staticmethod
    def _compute_file_hash(content: str) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            content: File content string

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _cache_path(file_hash: str) -> Path:
        """Get disk cache file path for a given content hash.

        Args:
            file_hash: SHA-256 hex digest of the reference file content

        Returns:
            Path to the cache JSON file
        """
        return _CACHE_DIR / f"{file_hash}.json"

    def _load_disk_cache(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Load tone profile from disk cache if it exists and hash matches.

        Args:
            file_hash: SHA-256 hex digest of current reference file content

        Returns:
            Cached tone profile, or None if no valid cache exists
        """
        cache_file = self._cache_path(file_hash)
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if data.get("file_hash") != file_hash:
                return None
            profile = data.get("profile")
            if profile:
                validate_tone_profile(profile)
                logger.info(f"Loaded tone profile from disk cache: {cache_file}")
                return profile
        except Exception as e:
            logger.warning(f"Disk cache read failed ({cache_file}): {e}")

        return None

    def _save_disk_cache(self, file_hash: str, profile: Dict[str, Any]) -> None:
        """Persist tone profile to disk cache.

        Args:
            file_hash: SHA-256 hex digest of the reference file content
            profile: Tone profile to cache
        """
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = self._cache_path(file_hash)
            payload = {"file_hash": file_hash, "profile": profile}
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"Tone profile saved to disk cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to write disk cache: {e}")

    def analyze_tone(self, reference_file: str | Path) -> Dict[str, Any]:
        """Analyze tone from reference document.

        Results are cached both in-memory (keyed by content hash) and on disk
        so that repeated calls—even across process restarts—skip the Claude API
        call when the reference file has not changed.

        Args:
            reference_file: Path to reference markdown file

        Returns:
            Tone profile dictionary with characteristics, vocabulary, patterns, style

        Raises:
            FileNotFoundError: If reference file doesn't exist
            ValueError: If analysis fails
        """
        reference_path = Path(reference_file)

        # Read reference file
        try:
            reference_content = read_text_sync(reference_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Reference file not found: {reference_file}")

        file_hash = self._compute_file_hash(reference_content)

        # 1. In-memory cache hit
        if self._tone_profile is not None and self._reference_file_hash == file_hash:
            logger.info("Using in-memory cached tone profile")
            return self._tone_profile

        # 2. Disk cache hit
        cached_profile = self._load_disk_cache(file_hash)
        if cached_profile is not None:
            self._tone_profile = cached_profile
            self._reference_file_hash = file_hash
            return cached_profile

        # 3. No cache – call Claude and persist result
        system_prompt = """You are a writing style analyst. Analyze the provided reference document and extract a comprehensive tone profile.

Your analysis should identify:
1. Characteristics: Overall tone, voice, and personality
2. Vocabulary: Word choices, technical level, formality
3. Patterns: Sentence structures, rhetorical devices, common phrases
4. Style: Formatting preferences, content organization, engagement techniques

Provide your analysis in JSON format with these exact keys: characteristics, vocabulary, patterns, style.
Each value should be a detailed string describing that aspect."""

        try:
            # System prompt and reference content are both static – mark both for
            # server-side prompt caching so subsequent calls within the 5-minute
            # window skip re-processing these large blocks entirely.
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze the writing style and tone from this"
                                    f" reference document:\n\n{reference_content}"
                                ),
                                "cache_control": {"type": "ephemeral"},
                            },
                            {
                                "type": "text",
                                "text": "Provide a comprehensive tone profile in JSON format.",
                            },
                        ],
                    }
                ],
            )

            self._log_cache_usage(response.usage)

            response_text = response.content[0].text
            tone_profile = self._extract_json(response_text)
            validate_tone_profile(tone_profile)

            # Persist to both caches
            self._save_disk_cache(file_hash, tone_profile)
            self._tone_profile = tone_profile
            self._reference_file_hash = file_hash

            logger.info(f"Tone profile analyzed from {reference_file}")
            return tone_profile

        except Exception as e:
            logger.error(f"Tone analysis failed: {e}")
            raise ValueError(f"Failed to analyze tone: {e}")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response.

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be extracted
        """
        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fence
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to find any JSON-like structure
        brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for match in matches:
            try:
                result = json.loads(match)
                if all(key in result for key in ["characteristics", "vocabulary", "patterns", "style"]):
                    return result
            except json.JSONDecodeError:
                continue

        raise ValueError("Could not extract valid JSON from response")

    def apply_tone(self, content: str, tone_profile: Optional[Dict[str, Any]] = None) -> str:
        """Apply tone profile to content using Claude.

        Args:
            content: Original content to adjust
            tone_profile: Tone profile to apply (uses cached if None)

        Returns:
            Content with tone applied

        Raises:
            ValueError: If no tone profile available
        """
        # Use provided or cached tone profile
        profile = tone_profile or self._tone_profile

        if profile is None:
            raise ValueError("No tone profile available. Call analyze_tone() first.")

        # The system prompt embeds the tone profile which is derived from the cached
        # reference file, so it is stable across calls within a session – cache it.
        system_prompt = f"""You are a skilled writer. Rewrite the provided content to match this specific tone profile:

Characteristics: {profile['characteristics']}
Vocabulary: {profile['vocabulary']}
Patterns: {profile['patterns']}
Style: {profile['style']}

Maintain the original meaning and key information, but adjust the writing style, word choices, and structure to match the tone profile."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"Rewrite this content to match the tone profile:\n\n{content}",
                    }
                ],
            )

            self._log_cache_usage(response.usage)
            adjusted_content = response.content[0].text
            logger.info("Applied tone to content")
            return adjusted_content

        except Exception as e:
            logger.error(f"Tone application failed: {e}")
            raise ValueError(f"Failed to apply tone: {e}")

    def validate_tone_match(self, content: str, tone_profile: Optional[Dict[str, Any]] = None) -> float:
        """Validate how well content matches tone profile.

        Args:
            content: Content to validate
            tone_profile: Tone profile to match against (uses cached if None)

        Returns:
            Match score from 0.0 to 1.0

        Raises:
            ValueError: If no tone profile available
        """
        # Use provided or cached tone profile
        profile = tone_profile or self._tone_profile

        if profile is None:
            raise ValueError("No tone profile available. Call analyze_tone() first.")

        # Static evaluation instructions – cache the system prompt.
        system_prompt = """You are a writing style evaluator. Compare the provided content against a tone profile and rate how well it matches.

Provide a score from 0.0 to 1.0 where:
- 0.0 = No match at all
- 0.5 = Partial match
- 1.0 = Perfect match

Respond with ONLY a number (e.g., "0.85")."""

        # The tone profile block is stable within a session; split it from the
        # variable content block so only the content-to-evaluate is uncached.
        tone_profile_text = (
            f"Tone Profile:\n"
            f"Characteristics: {profile['characteristics']}\n"
            f"Vocabulary: {profile['vocabulary']}\n"
            f"Patterns: {profile['patterns']}\n"
            f"Style: {profile['style']}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                temperature=0.1,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": tone_profile_text,
                                "cache_control": {"type": "ephemeral"},
                            },
                            {
                                "type": "text",
                                "text": f"\nContent to Evaluate:\n{content}\n\nScore (0.0 to 1.0):",
                            },
                        ],
                    }
                ],
            )

            self._log_cache_usage(response.usage)
            score_text = response.content[0].text.strip()
            score = float(score_text)

            # Clamp score to valid range
            score = max(0.0, min(1.0, score))

            logger.info(f"Tone match score: {score}")
            return score

        except Exception as e:
            logger.error(f"Tone validation failed: {e}")
            raise ValueError(f"Failed to validate tone: {e}")

    def get_cached_profile(self) -> Optional[Dict[str, Any]]:
        """Get in-memory cached tone profile if available.

        Returns:
            Cached tone profile or None
        """
        return self._tone_profile

    def clear_cache(self, clear_disk: bool = False) -> None:
        """Clear cached tone profile.

        Args:
            clear_disk: If True, also removes all on-disk cache files in
                        the cache directory in addition to the in-memory cache.
        """
        self._tone_profile = None
        self._reference_file_hash = None
        logger.info("In-memory tone profile cache cleared")

        if clear_disk:
            removed = 0
            if _CACHE_DIR.exists():
                for cache_file in _CACHE_DIR.glob("*.json"):
                    try:
                        cache_file.unlink()
                        removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file {cache_file}: {e}")
            logger.info(f"Disk cache cleared ({removed} file(s) removed)")
