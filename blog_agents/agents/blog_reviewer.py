"""BlogReviewer agent for reviewing and refining blog posts."""

import logging
import json
from typing import Dict, Any, List
from blog_agents.core.base_agent import BaseAgent
from blog_agents.config.agent_config import Config
from blog_agents.utils.file_manager import FileManager
from blog_agents.core.communication import BlogContentMessage

logger = logging.getLogger(__name__)


class BlogReviewer(BaseAgent):
    """Agent for reviewing blog posts for quality, accuracy, and tone."""

    def __init__(self, config: Config):
        """Initialize BlogReviewer.

        Args:
            config: System configuration
        """
        super().__init__(config, "BlogReviewer")

        self.file_manager = FileManager(config.blog_agents.output_dir)
        self.check_typos = config.blog_agents.blog_reviewer.check_typos
        self.check_reliability = config.blog_agents.blog_reviewer.check_reliability
        self.use_adaptive_learning = config.blog_agents.blog_reviewer.use_adaptive_learning

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute blog review and refinement.

        Args:
            input_data: Must contain 'title', 'content', 'sources'

        Returns:
            Dictionary with reviewed content and metadata
        """
        title = input_data.get("title", "")
        content = input_data.get("content", "")
        sources = input_data.get("sources", [])
        filename = input_data.get("filename", "")

        if not content:
            raise ValueError("Content is required for review")

        logger.info(f"Reviewing blog: {title}")

        # Step 1: Check for typos, duplications, and grammar
        corrections_made = []
        if self.check_typos:
            logger.info("Checking for typos and grammar issues")
            content, typo_corrections = await self._check_typos_and_grammar(content)
            corrections_made.extend(typo_corrections)
            logger.info(f"Made {len(typo_corrections)} grammar corrections")

        # Step 2: Refine tone to be more human-friendly
        logger.info("Refining tone for human-friendliness")
        content, tone_corrections = await self._refine_tone(content)
        corrections_made.extend(tone_corrections)
        logger.info(f"Made {len(tone_corrections)} tone adjustments")

        # Step 3: Verify reliability and accuracy
        reliability_score = 0.0
        reliability_notes = []
        if self.check_reliability:
            logger.info("Checking reliability and accuracy")
            reliability_score, reliability_notes = await self._check_reliability(
                content, sources
            )
            logger.info(f"Reliability score: {reliability_score:.2f}")

        # Step 4: Use adaptive-learner skill to learn from content
        learning_result = None
        if self.use_adaptive_learning:
            logger.info("Using adaptive-learner to acquire knowledge from content")
            learning_result = await self._apply_adaptive_learning(title, content)
            logger.info("Knowledge acquisition completed")

        # Step 5: Save reviewed content
        if filename:
            await self.file_manager.write_text(filename, content)
            logger.info(f"Reviewed blog saved to {filename}")

        result = {
            "title": title,
            "content": content,
            "corrections_made": corrections_made,
            "reliability_score": reliability_score,
            "reliability_notes": reliability_notes,
            "learning_result": learning_result,
            "filename": filename,
            "sources": sources
        }

        # Save review report
        await self.file_manager.write_json("review_report.json", result)

        return result

    async def _check_typos_and_grammar(self, content: str) -> tuple[str, List[str]]:
        """Check for typos, duplications, and grammar issues.

        Args:
            content: Blog content

        Returns:
            Tuple of (corrected content, list of corrections made)
        """
        system_prompt = """You are a professional Korean proofreader and editor.

Review the provided blog content and:
1. Fix typos and spelling errors
2. Remove duplicated words or phrases
3. Correct grammar issues
4. Ensure proper punctuation
5. Maintain the original meaning and structure

IMPORTANT: Respond with ONLY valid JSON, no additional text.

Format:
{
  "corrected_content": "the corrected full content here",
  "corrections": ["correction 1", "correction 2"]
}"""

        user_message = f"""Review this blog content for typos, duplications, and grammar issues:

{content}

Provide the corrected content and list of corrections made."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3
            )

            result = self._extract_json(response)

            corrected_content = result.get("corrected_content", content)
            corrections = result.get("corrections", [])

            return corrected_content, corrections

        except Exception as e:
            logger.error(f"Typo check failed: {e}")
            return content, []

    async def _refine_tone(self, content: str) -> tuple[str, List[str]]:
        """Refine tone to be more human-friendly.

        Args:
            content: Blog content

        Returns:
            Tuple of (refined content, list of tone adjustments)
        """
        system_prompt = """You are a professional Korean content editor specializing in human-friendly writing.

Refine the provided blog content to be more human-friendly:
1. Remove formal endings like "~~하죠", "~~합니다", "~~입니다" and replace with conversational but professional alternatives
2. Use natural Korean that a native speaker would use
3. Make the tone warm and engaging
4. Avoid overly academic or stiff language
5. Ensure smooth reading flow
6. Keep the content informative but accessible

IMPORTANT:
- The Korean should sound natural and fluent
- Avoid repetitive sentence patterns
- Use varied sentence structures
- Maintain professionalism while being friendly

Respond with ONLY valid JSON, no additional text.

Format:
{
  "refined_content": "the refined full content here",
  "adjustments": ["adjustment 1", "adjustment 2"]
}"""

        user_message = f"""Refine this blog content for a more human-friendly tone:

{content}

Provide the refined content and list of tone adjustments made."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5
            )

            result = self._extract_json(response)

            refined_content = result.get("refined_content", content)
            adjustments = result.get("adjustments", [])

            return refined_content, adjustments

        except Exception as e:
            logger.error(f"Tone refinement failed: {e}")
            return content, []

    async def _check_reliability(
        self, content: str, sources: List[Dict[str, Any]]
    ) -> tuple[float, List[str]]:
        """Check reliability and accuracy of content.

        Args:
            content: Blog content
            sources: Source references

        Returns:
            Tuple of (reliability score 0-1, list of reliability notes)
        """
        sources_text = "\n".join([f"- {s.get('title', '')}: {s.get('url', '')}" for s in sources])

        system_prompt = """You are a fact-checker and content reliability expert.

Evaluate the blog content for:
1. Factual accuracy based on provided sources
2. Claims that need verification
3. Potential misinformation or inaccuracies
4. Consistency with source material
5. Overall credibility

IMPORTANT: Respond with ONLY valid JSON, no additional text.

Format:
{
  "reliability_score": 0.85,
  "notes": ["note 1", "note 2"],
  "concerns": ["concern 1 if any"],
  "recommendations": ["recommendation 1"]
}"""

        user_message = f"""Evaluate the reliability of this blog content:

Content:
{content[:2000]}... (truncated)

Sources:
{sources_text}

Provide reliability assessment."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3
            )

            result = self._extract_json(response)

            reliability_score = result.get("reliability_score", 0.8)
            notes = result.get("notes", [])
            concerns = result.get("concerns", [])
            recommendations = result.get("recommendations", [])

            all_notes = notes + [f"Concern: {c}" for c in concerns] + [f"Recommendation: {r}" for r in recommendations]

            return reliability_score, all_notes

        except Exception as e:
            logger.error(f"Reliability check failed: {e}")
            return 0.8, []

    async def _apply_adaptive_learning(self, title: str, content: str) -> Dict[str, Any]:
        """Use adaptive-learner skill to acquire knowledge from content.

        Args:
            title: Blog title
            content: Blog content

        Returns:
            Learning result dictionary
        """
        system_prompt = """You are an adaptive learning system.

Read and analyze the provided blog content to acquire knowledge.

Extract and learn:
1. Key concepts and definitions
2. Important facts and statistics
3. Relationships between concepts
4. Practical applications
5. Best practices mentioned

IMPORTANT: Respond with ONLY valid JSON, no additional text.

Format:
{
  "key_concepts": ["concept 1", "concept 2"],
  "facts": ["fact 1", "fact 2"],
  "relationships": ["relationship 1"],
  "applications": ["application 1"],
  "best_practices": ["practice 1"]
}"""

        user_message = f"""Learn from this blog content:

Title: {title}

Content:
{content[:3000]}... (truncated if long)

Extract and organize the knowledge."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.4
            )

            result = self._extract_json(response)

            logger.info(f"Learned {len(result.get('key_concepts', []))} key concepts")

            return result

        except Exception as e:
            logger.error(f"Adaptive learning failed: {e}")
            return {}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response.

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON

        Raises:
            ValueError: If JSON cannot be extracted
        """
        import re

        # Remove any leading/trailing whitespace
        text = text.strip()

        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fence
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # Try to find JSON objects starting with { and ending with }
        start_idx = text.find('{')
        if start_idx != -1:
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = text[start_idx:i+1]
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                        break

        logger.error(f"Failed to extract JSON from response. First 500 chars: {text[:500]}")
        raise ValueError("Could not extract valid JSON from response")
