"""BlogPlanner agent for creating blog post outlines."""

import logging
import json
from typing import Dict, Any, List
from blog_agents.core.base_agent import BaseAgent
from blog_agents.config.agent_config import Config
from blog_agents.utils.file_manager import FileManager
from blog_agents.core.communication import BlogPlanMessage

logger = logging.getLogger(__name__)


class BlogPlanner(BaseAgent):
    """Agent for planning blog post structure and content."""

    def __init__(self, config: Config):
        """Initialize BlogPlanner.

        Args:
            config: System configuration
        """
        super().__init__(config, "BlogPlanner")

        self.file_manager = FileManager(config.blog_agents.output_dir)
        self.min_sections = config.blog_agents.blog_planner.min_sections
        self.max_sections = config.blog_agents.blog_planner.max_sections
        self.target_length = config.blog_agents.target_blog_length

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute blog planning.

        Args:
            input_data: Must contain 'selected_articles' and 'query'

        Returns:
            Dictionary with blog plan
        """
        articles = input_data.get("selected_articles", [])
        query = input_data.get("query", "")

        if not articles:
            raise ValueError("No articles provided for planning")

        logger.info(f"Planning blog based on {len(articles)} articles")

        # Step 1: Analyze articles
        analysis = await self._analyze_articles(query, articles)
        logger.info("Article analysis completed")

        # Step 2: Generate outline
        outline = await self._generate_outline(query, analysis)
        logger.info(f"Generated outline with {len(outline.get('sections', []))} sections")

        # Step 3: Extract key points
        key_points = await self._extract_key_points(articles, outline)
        logger.info(f"Extracted {len(key_points)} key points")

        # Step 4: Create structured plan
        plan = {
            "title": outline.get("title", f"Blog Post: {query}"),
            "sections": outline.get("sections", []),
            "key_points": key_points,
            "target_length": self.target_length,
            "sources_analyzed": len(articles),
            "sources": [
                {"title": article["title"], "url": article["url"]}
                for article in articles
            ]
        }

        # Save plan
        await self.file_manager.write_json("blog_plan.json", plan)

        return plan

    async def _analyze_articles(self, query: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze articles to identify themes and gaps.

        Args:
            query: Search query/topic
            articles: List of articles

        Returns:
            Analysis results
        """
        # Prepare article summaries
        article_summaries = []
        for idx, article in enumerate(articles):
            # Truncate content for analysis
            content_sample = article.get('content', '')[:2000]
            article_summaries.append({
                "title": article['title'],
                "url": article['url'],
                "content_sample": content_sample
            })

        system_prompt = """You are a content analyst. Analyze the provided articles and identify:

1. Common themes across articles
2. Unique perspectives or approaches
3. Gaps or missing information
4. Key concepts and terminology
5. Target audience level

IMPORTANT: Respond with ONLY valid JSON, no additional text.

Provide your analysis in this exact JSON format:
{
  "common_themes": ["theme1", "theme2"],
  "unique_perspectives": ["perspective1"],
  "gaps": ["gap1"],
  "key_concepts": ["concept1", "concept2"],
  "audience_level": "beginner|intermediate|advanced"
}"""

        user_message = f"""Topic: {query}

Articles:
{json.dumps(article_summaries, indent=2)}

Analyze these articles. Respond with ONLY valid JSON, no markdown or additional text."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5,
                cache_system=True,
            )

            logger.debug(f"Claude analysis response (first 300 chars): {response[:300]}")

            # Parse JSON response
            analysis = self._extract_json(response)

            # Validate and normalize analysis structure
            if not isinstance(analysis, dict):
                logger.warning(f"Analysis is not a dict: {type(analysis)}")
                raise ValueError("Invalid analysis structure")

            # Ensure required keys exist
            required_keys = ["common_themes", "unique_perspectives", "gaps", "key_concepts", "audience_level"]
            for key in required_keys:
                if key not in analysis:
                    logger.warning(f"Analysis missing key: {key}, adding default")
                    if key == "audience_level":
                        analysis[key] = "intermediate"
                    else:
                        analysis[key] = []

            logger.info("Successfully analyzed articles")
            return analysis

        except Exception as e:
            logger.error(f"Article analysis failed: {e}")
            # Return basic analysis
            return {
                "common_themes": [f"General discussion of {query}"],
                "unique_perspectives": ["Various approaches and methodologies"],
                "gaps": ["Detailed implementation examples"],
                "key_concepts": [query, "fundamentals", "best practices"],
                "audience_level": "intermediate"
            }

    async def _generate_outline(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate blog post outline.

        Args:
            query: Blog topic
            analysis: Article analysis results

        Returns:
            Outline with title and sections (always returns valid structure)
        """
        # Always return fallback if anything goes wrong
        try:
            system_prompt = f"""You are a blog content strategist. Create a comprehensive blog post outline.

Requirements:
- {self.min_sections} to {self.max_sections} main sections
- Each section should have a clear purpose and 2-3 subsections
- Target length: {self.target_length} words
- Logical flow from introduction to conclusion

IMPORTANT: You MUST respond with ONLY valid JSON, no additional text.

Provide the outline in this exact JSON format:
{{
  "title": "Engaging blog title",
  "sections": [
    {{
      "heading": "Section title",
      "purpose": "What this section covers",
      "subsections": ["Subsection 1", "Subsection 2"],
      "estimated_words": 300
    }}
  ]
}}"""

            user_message = f"""Topic: {query}

Analysis:
{json.dumps(analysis, indent=2)}

Create a comprehensive blog post outline. Respond with ONLY valid JSON, no markdown code blocks or additional text."""

            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                cache_system=True,
            )

            logger.debug(f"Claude outline response (first 500 chars): {response[:500]}")

            try:
                outline = self._extract_json(response)
            except Exception as json_error:
                logger.warning(f"JSON extraction failed: {json_error}, using fallback")
                return self._create_fallback_outline(query)

            # Validate and fix outline structure
            if not isinstance(outline, dict):
                logger.warning(f"Outline is not a dictionary: {type(outline)}, using fallback")
                return self._create_fallback_outline(query)

            if "sections" not in outline or not outline["sections"]:
                logger.warning("Outline missing or empty sections, using fallback")
                return self._create_fallback_outline(query)

            if not isinstance(outline["sections"], list):
                logger.warning(f"Sections is not a list: {type(outline['sections'])}, using fallback")
                return self._create_fallback_outline(query)

            # Fix each section
            fixed_sections = []
            for idx, section in enumerate(outline["sections"]):
                if not isinstance(section, dict):
                    logger.warning(f"Section {idx} is not a dict, skipping")
                    continue

                # Ensure all required fields
                fixed_section = {
                    "heading": section.get("heading", f"Section {idx + 1}"),
                    "purpose": section.get("purpose", ""),
                    "subsections": section.get("subsections", []),
                    "estimated_words": section.get("estimated_words", self.target_length // max(len(outline["sections"]), 1))
                }
                fixed_sections.append(fixed_section)

            if not fixed_sections:
                logger.warning("No valid sections after fixing, using fallback")
                return self._create_fallback_outline(query)

            # Build final outline
            final_outline = {
                "title": outline.get("title", f"Complete Guide to {query}"),
                "sections": fixed_sections
            }

            # Trim if too many sections
            if len(final_outline["sections"]) > self.max_sections:
                logger.warning(f"Trimming sections from {len(final_outline['sections'])} to {self.max_sections}")
                final_outline["sections"] = final_outline["sections"][:self.max_sections]

            logger.info(f"Successfully generated outline with {len(final_outline['sections'])} sections")
            return final_outline

        except Exception as e:
            # Catch ALL exceptions and return fallback
            logger.warning(f"Outline generation encountered error: {e}, using fallback")
            return self._create_fallback_outline(query)

    def _create_fallback_outline(self, query: str) -> Dict[str, Any]:
        """Create a fallback outline when generation fails.

        Args:
            query: Blog topic

        Returns:
            Basic outline structure
        """
        logger.warning("Creating fallback outline due to generation failure")

        words_per_section = self.target_length // self.min_sections

        return {
            "title": f"Complete Guide to {query}",
            "sections": [
                {
                    "heading": "Introduction",
                    "purpose": f"Introduce the topic of {query}",
                    "subsections": ["Overview", "Why It Matters"],
                    "estimated_words": words_per_section
                },
                {
                    "heading": "Key Concepts",
                    "purpose": f"Explain fundamental concepts related to {query}",
                    "subsections": ["Basic Principles", "Core Components"],
                    "estimated_words": words_per_section
                },
                {
                    "heading": "Best Practices",
                    "purpose": f"Share best practices for {query}",
                    "subsections": ["Common Approaches", "Expert Tips"],
                    "estimated_words": words_per_section
                },
                {
                    "heading": "Conclusion",
                    "purpose": "Summarize key takeaways",
                    "subsections": ["Summary", "Next Steps"],
                    "estimated_words": words_per_section
                }
            ]
        }

    async def _extract_key_points(
        self,
        articles: List[Dict[str, Any]],
        outline: Dict[str, Any]
    ) -> List[str]:
        """Extract key points from articles relevant to outline.

        Args:
            articles: Source articles
            outline: Blog outline

        Returns:
            List of key points
        """
        # Prepare content samples
        content_samples = []
        for article in articles:
            content_samples.append({
                "title": article["title"],
                "content": article.get("content", "")[:1500]
            })

        # Get section headings
        section_headings = [s.get("heading", "") for s in outline.get("sections", [])]

        system_prompt = """You are a research assistant. Extract key points from the articles that are relevant to the blog outline sections.

For each section, identify:
- Important facts or statistics
- Notable quotes or insights
- Examples or case studies
- Best practices or recommendations

IMPORTANT: Respond with ONLY a valid JSON array of strings, no additional text.

Format: ["key point 1", "key point 2", "key point 3"]"""

        user_message = f"""Outline Sections:
{json.dumps(section_headings, indent=2)}

Articles:
{json.dumps(content_samples, indent=2)}

Extract key points relevant to the outline sections. Respond with ONLY a JSON array of strings, no markdown or additional text."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5,
                cache_system=True,
            )

            logger.debug(f"Claude key points response (first 300 chars): {response[:300]}")

            # Extract key points
            key_points = self._extract_json(response)

            # Handle different response formats
            if isinstance(key_points, dict):
                # Try common keys
                for key in ["key_points", "points", "items", "results"]:
                    if key in key_points and isinstance(key_points[key], list):
                        key_points = key_points[key]
                        break
                else:
                    logger.warning(f"Dict response with unexpected keys: {key_points.keys()}")
                    return []

            if not isinstance(key_points, list):
                logger.warning(f"Key points not a list: {type(key_points)}")
                return []

            # Filter to ensure all items are strings
            key_points = [str(point) for point in key_points if point]

            logger.info(f"Successfully extracted {len(key_points)} key points")
            return key_points

        except Exception as e:
            logger.error(f"Key points extraction failed: {e}")
            # Return empty list, not critical for blog generation
            return []

    def _extract_json(self, text: str) -> Dict[str, Any] | List[Any]:
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

        # Try to find JSON block in markdown code fence (with or without language)
        # Match ```json or ``` followed by JSON
        json_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # Try to find JSON objects starting with { and ending with }
        # More lenient pattern that handles nested structures
        start_idx = text.find('{')
        if start_idx != -1:
            # Find the matching closing brace
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

        # Try to find JSON arrays
        start_idx = text.find('[')
        if start_idx != -1:
            bracket_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '[':
                    bracket_count += 1
                elif text[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        try:
                            json_str = text[start_idx:i+1]
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                        break

        # Log the problematic text for debugging
        logger.error(f"Failed to extract JSON from response. First 500 chars: {text[:500]}")
        raise ValueError("Could not extract valid JSON from response")
