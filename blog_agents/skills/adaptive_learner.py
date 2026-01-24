"""AdaptiveLearner skill for domain learning and fact verification."""

import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, AsyncAnthropic
from blog_agents.config.agent_config import Config

logger = logging.getLogger(__name__)


class AdaptiveLearner:
    """Skill for learning domain knowledge and verifying content accuracy."""

    def __init__(self, config: Config):
        """Initialize AdaptiveLearner.

        Args:
            config: System configuration
        """
        self.config = config
        self.client = Anthropic(api_key=config.ai.api_key)
        self.async_client = AsyncAnthropic(api_key=config.ai.api_key)
        self.model = config.ai.model

        # Cache for domain knowledge
        self._domain_knowledge: Optional[Dict[str, Any]] = None
        self._current_domain: Optional[str] = None

    async def analyze_domain(self, content: str) -> Dict[str, Any]:
        """Analyze content to identify its domain and key topics.

        Args:
            content: Content to analyze

        Returns:
            Dictionary with domain, topics, and technical_level

        Raises:
            ValueError: If analysis fails
        """
        system_prompt = """You are a domain analysis expert. Analyze the provided content and identify:
1. Primary domain/field (e.g., technology, health, finance, science)
2. Key topics and concepts covered
3. Technical level (beginner, intermediate, advanced)
4. Specific subject areas that require fact-checking

Provide your analysis in JSON format with these keys:
- domain: string
- topics: list of strings
- technical_level: string
- fact_check_areas: list of specific claims or statements that should be verified"""

        user_message = f"""Analyze this content and identify its domain:

{content}

Provide domain analysis in JSON format."""

        try:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            response_text = response.content[0].text
            domain_info = self._extract_json(response_text)

            logger.info(f"Domain identified: {domain_info.get('domain', 'unknown')}")
            return domain_info

        except Exception as e:
            logger.error(f"Domain analysis failed: {e}")
            raise ValueError(f"Failed to analyze domain: {e}")

    async def learn_domain(self, domain_info: Dict[str, Any]) -> Dict[str, Any]:
        """Learn about the domain to build knowledge base.

        Args:
            domain_info: Domain information from analyze_domain()

        Returns:
            Domain knowledge dictionary

        Raises:
            ValueError: If learning fails
        """
        domain = domain_info.get("domain", "")
        topics = domain_info.get("topics", [])

        # Check cache
        if self._domain_knowledge and self._current_domain == domain:
            logger.info("Using cached domain knowledge")
            return self._domain_knowledge

        system_prompt = f"""You are a domain expert in {domain}. Provide comprehensive knowledge about the following topics:

Topics: {', '.join(topics)}

Your knowledge should include:
1. Key concepts and definitions
2. Current best practices and standards
3. Common misconceptions
4. Recent developments (as of your knowledge cutoff)
5. Authoritative sources and references

Provide your knowledge in JSON format with these keys:
- key_concepts: dict mapping concept names to definitions
- best_practices: list of strings
- common_misconceptions: list of strings
- recent_developments: list of strings
- authoritative_sources: list of strings"""

        user_message = f"""Provide comprehensive knowledge about {domain}, focusing on: {', '.join(topics)}

Provide domain knowledge in JSON format."""

        try:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.2,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            response_text = response.content[0].text
            domain_knowledge = self._extract_json(response_text)

            # Cache the knowledge
            self._domain_knowledge = domain_knowledge
            self._current_domain = domain

            logger.info(f"Domain knowledge acquired for: {domain}")
            return domain_knowledge

        except Exception as e:
            logger.error(f"Domain learning failed: {e}")
            raise ValueError(f"Failed to learn domain: {e}")

    async def verify_facts(
        self,
        content: str,
        domain_info: Dict[str, Any],
        domain_knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify factual accuracy of content against domain knowledge.

        Args:
            content: Content to verify
            domain_info: Domain information
            domain_knowledge: Domain knowledge base

        Returns:
            Verification results with issues found

        Raises:
            ValueError: If verification fails
        """
        fact_check_areas = domain_info.get("fact_check_areas", [])

        system_prompt = f"""You are a fact-checking expert with deep knowledge of {domain_info.get('domain', 'this field')}.

Domain Knowledge:
{json.dumps(domain_knowledge, indent=2)}

Carefully review the content and identify:
1. Factual errors or inaccuracies
2. Outdated information
3. Misleading statements
4. Unsupported claims
5. Contradictions with established knowledge

Focus especially on these areas: {', '.join(fact_check_areas)}

Provide your findings in JSON format with these keys:
- is_accurate: boolean (overall accuracy assessment)
- accuracy_score: float (0.0 to 1.0)
- factual_errors: list of dicts with keys: "claim", "issue", "correction", "severity" (low/medium/high)
- outdated_info: list of dicts with keys: "statement", "reason", "update"
- unsupported_claims: list of strings
- overall_assessment: string summarizing the verification"""

        user_message = f"""Verify the factual accuracy of this content:

{content}

Provide verification results in JSON format."""

        try:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.2,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            response_text = response.content[0].text
            verification_results = self._extract_json(response_text)

            accuracy_score = verification_results.get("accuracy_score", 0.0)
            logger.info(f"Fact verification completed. Accuracy score: {accuracy_score}")

            return verification_results

        except Exception as e:
            logger.error(f"Fact verification failed: {e}")
            raise ValueError(f"Failed to verify facts: {e}")

    async def suggest_improvements(
        self,
        content: str,
        verification_results: Dict[str, Any],
        domain_knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest improvements based on verification results.

        Args:
            content: Original content
            verification_results: Results from verify_facts()
            domain_knowledge: Domain knowledge base

        Returns:
            Improvement suggestions

        Raises:
            ValueError: If suggestion generation fails
        """
        system_prompt = f"""You are a content improvement expert. Based on the fact-checking results, suggest specific improvements to the content.

Domain Knowledge:
{json.dumps(domain_knowledge, indent=2)}

Verification Results:
{json.dumps(verification_results, indent=2)}

Provide improvement suggestions in JSON format with these keys:
- corrections: list of dicts with "original_text", "corrected_text", "reason"
- additions: list of dicts with "location", "content_to_add", "reason"
- removals: list of dicts with "text_to_remove", "reason"
- enhancements: list of dicts with "section", "improvement", "reason"
- priority: string (high/medium/low) - overall priority of changes"""

        user_message = f"""Original content:

{content}

Suggest specific improvements to address the issues found.

Provide suggestions in JSON format."""

        try:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            response_text = response.content[0].text
            suggestions = self._extract_json(response_text)

            logger.info("Improvement suggestions generated")
            return suggestions

        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            raise ValueError(f"Failed to generate suggestions: {e}")

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
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        raise ValueError("Could not extract valid JSON from response")

    def clear_cache(self):
        """Clear cached domain knowledge."""
        self._domain_knowledge = None
        self._current_domain = None
        logger.info("Domain knowledge cache cleared")
