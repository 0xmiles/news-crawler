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

Provide your analysis in JSON format with these keys: common_themes, unique_perspectives, gaps, key_concepts, audience_level."""

        user_message = f"""Topic: {query}

Articles:
{json.dumps(article_summaries, indent=2)}

Analyze these articles and provide insights in JSON format."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5
            )

            # Parse JSON response
            analysis = self._extract_json(response)
            return analysis

        except Exception as e:
            logger.error(f"Article analysis failed: {e}")
            # Return basic analysis
            return {
                "common_themes": ["General discussion of " + query],
                "unique_perspectives": [],
                "gaps": [],
                "key_concepts": [query],
                "audience_level": "intermediate"
            }

    async def _generate_outline(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate blog post outline.

        Args:
            query: Blog topic
            analysis: Article analysis results

        Returns:
            Outline with title and sections
        """
        system_prompt = f"""You are a blog content strategist. Create a comprehensive blog post outline.

Requirements:
- {self.min_sections} to {self.max_sections} main sections
- Each section should have a clear purpose and 2-3 subsections
- Target length: {self.target_length} words
- Logical flow from introduction to conclusion

Provide the outline in JSON format:
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

Create a comprehensive blog post outline in JSON format."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7
            )

            outline = self._extract_json(response)

            # Validate outline
            if "sections" not in outline or not outline["sections"]:
                raise ValueError("Invalid outline structure")

            # Ensure section count is within range
            sections = outline["sections"]
            if len(sections) < self.min_sections:
                logger.warning(f"Outline has fewer sections than minimum ({self.min_sections})")
            elif len(sections) > self.max_sections:
                logger.warning(f"Outline has more sections than maximum ({self.max_sections})")
                outline["sections"] = sections[:self.max_sections]

            return outline

        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            raise

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

Provide a list of concise key points (one sentence each)."""

        user_message = f"""Outline Sections:
{json.dumps(section_headings, indent=2)}

Articles:
{json.dumps(content_samples, indent=2)}

Extract key points relevant to the outline sections. Return as a JSON array of strings."""

        try:
            response = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5
            )

            # Extract key points
            key_points = self._extract_json(response)

            # Ensure it's a list
            if isinstance(key_points, dict) and "key_points" in key_points:
                key_points = key_points["key_points"]

            if not isinstance(key_points, list):
                logger.warning("Key points not in expected format")
                return []

            return key_points

        except Exception as e:
            logger.error(f"Key points extraction failed: {e}")
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
        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fence
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to find any JSON structure
        brace_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[.*?\])'
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        raise ValueError("Could not extract valid JSON from response")
