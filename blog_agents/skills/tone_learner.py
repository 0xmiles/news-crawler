"""ToneLearner skill for analyzing and applying writing tone."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from anthropic import Anthropic
from blog_agents.config.agent_config import Config
from blog_agents.utils.file_manager import read_text_sync
from blog_agents.utils.validators import validate_tone_profile

logger = logging.getLogger(__name__)


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

        # Cache for tone profile
        self._tone_profile: Optional[Dict[str, Any]] = None
        self._reference_file_path: Optional[Path] = None

    def analyze_tone(self, reference_file: str | Path) -> Dict[str, Any]:
        """Analyze tone from reference document.

        Args:
            reference_file: Path to reference markdown file

        Returns:
            Tone profile dictionary with characteristics, vocabulary, patterns, style

        Raises:
            FileNotFoundError: If reference file doesn't exist
            ValueError: If analysis fails
        """
        reference_path = Path(reference_file)

        # Check cache
        if self._tone_profile is not None and self._reference_file_path == reference_path:
            logger.info("Using cached tone profile")
            return self._tone_profile

        # Read reference file
        try:
            reference_content = read_text_sync(reference_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Reference file not found: {reference_file}")

        # Prepare prompt for Claude
        system_prompt = """You are a writing style analyst. Analyze the provided reference document and extract a comprehensive tone profile.

Your analysis should identify:
1. Characteristics: Overall tone, voice, and personality
2. Vocabulary: Word choices, technical level, formality
3. Patterns: Sentence structures, rhetorical devices, common phrases
4. Style: Formatting preferences, content organization, engagement techniques

Provide your analysis in JSON format with these exact keys: characteristics, vocabulary, patterns, style.
Each value should be a detailed string describing that aspect."""

        user_message = f"""Analyze the writing style and tone from this reference document:

{reference_content}

Provide a comprehensive tone profile in JSON format."""

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for consistent analysis
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Extract response
            response_text = response.content[0].text

            # Parse JSON from response
            # Try to find JSON in the response
            tone_profile = self._extract_json(response_text)

            # Validate tone profile
            validate_tone_profile(tone_profile)

            # Cache the profile
            self._tone_profile = tone_profile
            self._reference_file_path = reference_path

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

        # Create prompt for tone application
        system_prompt = f"""You are a skilled writer. Rewrite the provided content to match this specific tone profile:

Characteristics: {profile['characteristics']}
Vocabulary: {profile['vocabulary']}
Patterns: {profile['patterns']}
Style: {profile['style']}

Maintain the original meaning and key information, but adjust the writing style, word choices, and structure to match the tone profile."""

        user_message = f"""Rewrite this content to match the tone profile:

{content}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

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

        # Create validation prompt
        system_prompt = """You are a writing style evaluator. Compare the provided content against a tone profile and rate how well it matches.

Provide a score from 0.0 to 1.0 where:
- 0.0 = No match at all
- 0.5 = Partial match
- 1.0 = Perfect match

Respond with ONLY a number (e.g., "0.85")."""

        user_message = f"""Tone Profile:
Characteristics: {profile['characteristics']}
Vocabulary: {profile['vocabulary']}
Patterns: {profile['patterns']}
Style: {profile['style']}

Content to Evaluate:
{content}

Score (0.0 to 1.0):"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

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
        """Get cached tone profile if available.

        Returns:
            Cached tone profile or None
        """
        return self._tone_profile

    def clear_cache(self):
        """Clear cached tone profile."""
        self._tone_profile = None
        self._reference_file_path = None
        logger.info("Tone profile cache cleared")
