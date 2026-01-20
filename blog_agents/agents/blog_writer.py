"""BlogWriter agent for writing blog posts with tone application."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from blog_agents.core.base_agent import BaseAgent
from blog_agents.config.agent_config import Config
from blog_agents.utils.file_manager import FileManager
from blog_agents.skills.tone_learner import ToneLearner
from blog_agents.core.communication import BlogContentMessage

logger = logging.getLogger(__name__)


class BlogWriter(BaseAgent):
    """Agent for writing blog posts with tone application."""

    def __init__(self, config: Config):
        """Initialize BlogWriter.

        Args:
            config: System configuration
        """
        super().__init__(config, "BlogWriter")

        self.file_manager = FileManager(config.blog_agents.output_dir)
        self.tone_learner = ToneLearner(config)
        self.apply_tone = config.blog_agents.blog_writer.apply_tone_analysis
        self.section_word_target = config.blog_agents.blog_writer.section_word_target
        self.reference_file = config.blog_agents.reference_file

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute blog writing.

        Args:
            input_data: Must contain 'title', 'sections', 'key_points', 'sources'

        Returns:
            Dictionary with blog content
        """
        title = input_data.get("title", "")
        sections = input_data.get("sections", [])
        key_points = input_data.get("key_points", [])
        sources = input_data.get("sources", [])

        if not title or not sections:
            raise ValueError("Title and sections are required for blog writing")

        logger.info(f"Writing blog: {title}")

        # Step 1: Load tone profile if enabled
        tone_profile = None
        if self.apply_tone:
            try:
                logger.info(f"Analyzing tone from {self.reference_file}")
                tone_profile = self.tone_learner.analyze_tone(self.reference_file)
                logger.info("Tone profile loaded")
            except Exception as e:
                logger.warning(f"Tone analysis failed: {e}. Writing without tone application.")
                self.apply_tone = False

        # Step 2: Write introduction
        introduction = await self._write_introduction(title, sections, tone_profile)
        logger.info("Introduction written")

        # Step 3: Write each section
        section_contents = []
        for idx, section in enumerate(sections):
            logger.info(f"Writing section {idx + 1}/{len(sections)}: {section.get('heading', '')}")
            content = await self._write_section(
                section=section,
                key_points=key_points,
                tone_profile=tone_profile
            )
            section_contents.append(content)

        # Step 4: Write conclusion
        conclusion = await self._write_conclusion(title, sections, tone_profile)
        logger.info("Conclusion written")

        # Step 5: Combine all parts
        full_content = self._assemble_blog(
            title=title,
            introduction=introduction,
            sections=sections,
            section_contents=section_contents,
            conclusion=conclusion,
            sources=sources
        )

        # Step 6: Review and refine
        if self.apply_tone and tone_profile:
            logger.info("Reviewing and refining tone")
            full_content = await self._review_and_refine(full_content, tone_profile)

        # Step 7: Calculate metrics
        word_count = len(full_content.split())
        sections_count = len(sections)

        # Step 8: Save blog
        filename = self._generate_filename(title)
        await self.file_manager.write_text(filename, full_content)
        logger.info(f"Blog saved to {filename}")

        result = {
            "title": title,
            "content": full_content,
            "word_count": word_count,
            "sections_count": sections_count,
            "tone_applied": self.apply_tone,
            "filename": filename,
            "sources": [s.get("url", "") for s in sources]
        }

        return result

    async def _write_introduction(
        self,
        title: str,
        sections: List[Dict[str, Any]],
        tone_profile: Dict[str, Any] = None
    ) -> str:
        """Write blog introduction.

        Args:
            title: Blog title
            sections: List of sections
            tone_profile: Optional tone profile

        Returns:
            Introduction text
        """
        section_headings = [s.get("heading", "") for s in sections]

        # Build system prompt
        if tone_profile:
            system_prompt = f"""You are a skilled blog writer. Write an engaging introduction for a blog post.

Apply this tone profile:
- Characteristics: {tone_profile['characteristics']}
- Vocabulary: {tone_profile['vocabulary']}
- Style: {tone_profile['style']}

The introduction should:
1. Hook the reader with a compelling opening
2. Introduce the topic and its relevance
3. Preview what the post will cover
4. Be approximately 150-200 words"""
        else:
            system_prompt = """You are a skilled blog writer. Write an engaging introduction for a blog post.

The introduction should:
1. Hook the reader with a compelling opening
2. Introduce the topic and its relevance
3. Preview what the post will cover
4. Be approximately 150-200 words"""

        user_message = f"""Blog Title: {title}

Sections to Preview:
{chr(10).join(f"- {h}" for h in section_headings)}

Write an engaging introduction."""

        response = await self.call_claude(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7
        )

        return response.strip()

    async def _write_section(
        self,
        section: Dict[str, Any],
        key_points: List[str],
        tone_profile: Dict[str, Any] = None
    ) -> str:
        """Write a blog section.

        Args:
            section: Section metadata
            key_points: Key points to incorporate
            tone_profile: Optional tone profile

        Returns:
            Section content
        """
        heading = section.get("heading", "")
        purpose = section.get("purpose", "")
        subsections = section.get("subsections", [])
        target_words = section.get("estimated_words", self.section_word_target)

        # Filter relevant key points
        relevant_points = [kp for kp in key_points if any(word.lower() in kp.lower() for word in heading.split())][:5]

        # Build system prompt
        if tone_profile:
            system_prompt = f"""You are a skilled blog writer. Write a comprehensive section for a blog post.

Apply this tone profile:
- Characteristics: {tone_profile['characteristics']}
- Vocabulary: {tone_profile['vocabulary']}
- Patterns: {tone_profile['patterns']}
- Style: {tone_profile['style']}

Requirements:
- Target length: ~{target_words} words
- Cover the subsections thoroughly
- Incorporate relevant key points naturally
- Use clear headings for subsections
- Include examples where appropriate"""
        else:
            system_prompt = f"""You are a skilled blog writer. Write a comprehensive section for a blog post.

Requirements:
- Target length: ~{target_words} words
- Cover the subsections thoroughly
- Incorporate relevant key points naturally
- Use clear headings for subsections
- Include examples where appropriate"""

        user_message = f"""Section Heading: {heading}

Purpose: {purpose}

Subsections to Cover:
{chr(10).join(f"- {s}" for s in subsections)}

Relevant Key Points:
{chr(10).join(f"- {kp}" for kp in relevant_points) if relevant_points else "No specific key points"}

Write this section in markdown format."""

        response = await self.call_claude(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=target_words * 2  # Allow some buffer
        )

        return response.strip()

    async def _write_conclusion(
        self,
        title: str,
        sections: List[Dict[str, Any]],
        tone_profile: Dict[str, Any] = None
    ) -> str:
        """Write blog conclusion.

        Args:
            title: Blog title
            sections: List of sections
            tone_profile: Optional tone profile

        Returns:
            Conclusion text
        """
        section_headings = [s.get("heading", "") for s in sections]

        # Build system prompt
        if tone_profile:
            system_prompt = f"""You are a skilled blog writer. Write a compelling conclusion for a blog post.

Apply this tone profile:
- Characteristics: {tone_profile['characteristics']}
- Vocabulary: {tone_profile['vocabulary']}
- Style: {tone_profile['style']}

The conclusion should:
1. Summarize key takeaways
2. Reinforce the main message
3. End with a call-to-action or thought-provoking statement
4. Be approximately 100-150 words"""
        else:
            system_prompt = """You are a skilled blog writer. Write a compelling conclusion for a blog post.

The conclusion should:
1. Summarize key takeaways
2. Reinforce the main message
3. End with a call-to-action or thought-provoking statement
4. Be approximately 100-150 words"""

        user_message = f"""Blog Title: {title}

Sections Covered:
{chr(10).join(f"- {h}" for h in section_headings)}

Write a compelling conclusion."""

        response = await self.call_claude(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7
        )

        return response.strip()

    def _assemble_blog(
        self,
        title: str,
        introduction: str,
        sections: List[Dict[str, Any]],
        section_contents: List[str],
        conclusion: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """Assemble complete blog post.

        Args:
            title: Blog title
            introduction: Introduction text
            sections: Section metadata
            section_contents: Section content texts
            conclusion: Conclusion text
            sources: Source references

        Returns:
            Complete blog post in markdown
        """
        parts = []

        # Title
        parts.append(f"# {title}\n")

        # Introduction
        parts.append(introduction)
        parts.append("")

        # Sections
        for section, content in zip(sections, section_contents):
            heading = section.get("heading", "")
            parts.append(f"## {heading}\n")
            parts.append(content)
            parts.append("")

        # Conclusion
        parts.append("## Conclusion\n")
        parts.append(conclusion)
        parts.append("")

        # Sources
        if sources:
            parts.append("## References\n")
            for idx, source in enumerate(sources, 1):
                title_text = source.get("title", "Source")
                url = source.get("url", "")
                parts.append(f"{idx}. [{title_text}]({url})")
            parts.append("")

        # Footer
        parts.append("---")
        parts.append(f"\n*Generated on {datetime.now().strftime('%Y-%m-%d')}*")

        return "\n".join(parts)

    async def _review_and_refine(self, content: str, tone_profile: Dict[str, Any]) -> str:
        """Review and refine blog post for tone consistency.

        Args:
            content: Blog content
            tone_profile: Tone profile

        Returns:
            Refined content
        """
        # Check tone match
        try:
            score = self.tone_learner.validate_tone_match(content, tone_profile)
            logger.info(f"Tone match score: {score}")

            # If tone match is good enough, return as is
            if score >= 0.75:
                return content

            # Otherwise, apply tone adjustment
            logger.info("Applying tone refinement")
            refined_content = self.tone_learner.apply_tone(content, tone_profile)
            return refined_content

        except Exception as e:
            logger.warning(f"Tone refinement failed: {e}")
            return content

    def _generate_filename(self, title: str) -> str:
        """Generate filename from title.

        Args:
            title: Blog title

        Returns:
            Filename
        """
        # Clean title
        import re
        clean_title = re.sub(r'[^\w\s-]', '', title.lower())
        clean_title = re.sub(r'[-\s]+', '-', clean_title)
        clean_title = clean_title[:50]  # Limit length

        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d')

        return f"{clean_title}-{timestamp}.md"
