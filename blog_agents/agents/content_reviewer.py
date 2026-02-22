"""ContentReviewer agent for reviewing and improving blog content."""

import logging
from typing import Dict, Any, List
from blog_agents.core.base_agent import BaseAgent
from blog_agents.config.agent_config import Config
from blog_agents.skills.adaptive_learner import AdaptiveLearner

logger = logging.getLogger(__name__)


class ContentReviewer(BaseAgent):
    """Agent for reviewing blog content for spelling, grammar, and factual accuracy."""

    def __init__(self, config: Config):
        """Initialize ContentReviewer.

        Args:
            config: System configuration
        """
        super().__init__(config, "ContentReviewer")

        self.adaptive_learner = AdaptiveLearner(config)
        self.enable_spell_check = config.blog_agents.content_reviewer.enable_spell_check
        self.enable_fact_check = config.blog_agents.content_reviewer.enable_fact_check
        self.auto_apply_corrections = config.blog_agents.content_reviewer.auto_apply_corrections

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content review.

        Args:
            input_data: Must contain 'content' (string) and optionally 'title'

        Returns:
            Dictionary with reviewed content and issues found
        """
        content = input_data.get("content", "")
        title = input_data.get("title", "Untitled")

        if not content:
            raise ValueError("Content is required for review")

        logger.info(f"Reviewing content: {title}")

        review_results = {
            "original_content": content,
            "reviewed_content": content,
            "issues_found": [],
            "corrections_applied": [],
            "accuracy_score": 1.0,
            "spell_check_performed": False,
            "fact_check_performed": False
        }

        # Step 1: Spell and grammar check
        if self.enable_spell_check:
            logger.info("Performing spell and grammar check")
            spell_results = await self._check_spelling_grammar(content)
            review_results["spell_check_performed"] = True
            review_results["issues_found"].extend(spell_results.get("issues", []))

            if self.auto_apply_corrections and spell_results.get("corrected_content"):
                review_results["reviewed_content"] = spell_results["corrected_content"]
                review_results["corrections_applied"].extend(spell_results.get("corrections", []))
                logger.info(f"Applied {len(spell_results.get('corrections', []))} spelling/grammar corrections")

        # Step 2: Fact checking with adaptive learning
        if self.enable_fact_check:
            logger.info("Performing fact check with domain learning")

            # Analyze domain
            domain_info = await self.adaptive_learner.analyze_domain(
                review_results["reviewed_content"]
            )
            logger.info(f"Domain analyzed: {domain_info.get('domain', 'unknown')}")

            # Learn domain
            domain_knowledge = await self.adaptive_learner.learn_domain(domain_info)
            logger.info("Domain knowledge acquired")

            # Verify facts
            verification_results = await self.adaptive_learner.verify_facts(
                content=review_results["reviewed_content"],
                domain_info=domain_info,
                domain_knowledge=domain_knowledge
            )
            review_results["fact_check_performed"] = True
            review_results["accuracy_score"] = verification_results.get("accuracy_score", 1.0)

            # Add factual issues
            for error in verification_results.get("factual_errors", []):
                review_results["issues_found"].append({
                    "type": "factual_error",
                    "severity": error.get("severity", "medium"),
                    "claim": error.get("claim", ""),
                    "issue": error.get("issue", ""),
                    "correction": error.get("correction", "")
                })

            for outdated in verification_results.get("outdated_info", []):
                review_results["issues_found"].append({
                    "type": "outdated_info",
                    "severity": "medium",
                    "statement": outdated.get("statement", ""),
                    "reason": outdated.get("reason", ""),
                    "update": outdated.get("update", "")
                })

            for unsupported in verification_results.get("unsupported_claims", []):
                review_results["issues_found"].append({
                    "type": "unsupported_claim",
                    "severity": "low",
                    "claim": unsupported
                })

            # Get improvement suggestions
            if review_results["issues_found"]:
                logger.info("Generating improvement suggestions")
                suggestions = await self.adaptive_learner.suggest_improvements(
                    content=review_results["reviewed_content"],
                    verification_results=verification_results,
                    domain_knowledge=domain_knowledge
                )

                # Apply corrections if enabled
                if self.auto_apply_corrections:
                    review_results["reviewed_content"] = await self._apply_improvements(
                        content=review_results["reviewed_content"],
                        suggestions=suggestions
                    )
                    review_results["corrections_applied"].extend(
                        suggestions.get("corrections", [])
                    )
                    logger.info(f"Applied {len(suggestions.get('corrections', []))} factual corrections")

                review_results["improvement_suggestions"] = suggestions

        # Step 3: Generate review summary
        review_results["review_summary"] = self._generate_review_summary(review_results)

        logger.info(f"Review completed. Found {len(review_results['issues_found'])} issues")

        return review_results

    async def _check_spelling_grammar(self, content: str) -> Dict[str, Any]:
        """Check spelling and grammar using Claude.

        Args:
            content: Content to check

        Returns:
            Dictionary with issues and corrected content
        """
        system_prompt = """You are an expert proofreader and grammar checker. Review the provided content for:
1. Spelling errors
2. Grammar mistakes
3. Punctuation errors
4. Style inconsistencies
5. Sentence structure issues

Provide your findings in JSON format with these keys:
- issues: list of dicts with "type", "original", "correction", "explanation"
- corrected_content: string with all corrections applied
- total_issues: integer
- issue_summary: string summarizing the types of issues found"""

        user_message = f"""Review this content for spelling and grammar errors:

{content}

Provide results in JSON format."""

        try:
            response_text = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.2,
                cache_system=True,
            )

            # Parse JSON response
            import json
            result = self._extract_json(response_text)

            # Format issues for output
            formatted_issues = []
            for issue in result.get("issues", []):
                formatted_issues.append({
                    "type": f"spelling_grammar_{issue.get('type', 'error')}",
                    "severity": "low",
                    "original": issue.get("original", ""),
                    "correction": issue.get("correction", ""),
                    "explanation": issue.get("explanation", "")
                })

            return {
                "issues": formatted_issues,
                "corrected_content": result.get("corrected_content", content),
                "corrections": [
                    {
                        "original_text": issue.get("original", ""),
                        "corrected_text": issue.get("correction", ""),
                        "reason": issue.get("explanation", "")
                    }
                    for issue in result.get("issues", [])
                ],
                "total_issues": result.get("total_issues", 0)
            }

        except Exception as e:
            logger.error(f"Spell check failed: {e}")
            return {"issues": [], "corrected_content": content, "corrections": [], "total_issues": 0}

    async def _apply_improvements(
        self,
        content: str,
        suggestions: Dict[str, Any]
    ) -> str:
        """Apply improvement suggestions to content.

        Args:
            content: Original content
            suggestions: Suggestions from adaptive_learner

        Returns:
            Improved content
        """
        system_prompt = """You are a content editor. Apply the provided improvement suggestions to the content.

Apply corrections precisely and maintain the original structure and style as much as possible.
Only make changes that are specified in the suggestions."""

        corrections = suggestions.get("corrections", [])
        additions = suggestions.get("additions", [])
        removals = suggestions.get("removals", [])

        user_message = f"""Original content:
{content}

Apply these improvements:

Corrections:
{json.dumps(corrections, indent=2) if corrections else "None"}

Additions:
{json.dumps(additions, indent=2) if additions else "None"}

Removals:
{json.dumps(removals, indent=2) if removals else "None"}

Return the improved content."""

        try:
            import json
            improved_content = await self.call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                cache_system=True,
            )

            return improved_content.strip()

        except Exception as e:
            logger.error(f"Failed to apply improvements: {e}")
            return content

    def _generate_review_summary(self, review_results: Dict[str, Any]) -> str:
        """Generate human-readable review summary.

        Args:
            review_results: Review results dictionary

        Returns:
            Summary string
        """
        summary_parts = []

        total_issues = len(review_results["issues_found"])
        total_corrections = len(review_results["corrections_applied"])

        summary_parts.append(f"Content Review Summary")
        summary_parts.append(f"{'=' * 50}")

        if review_results["spell_check_performed"]:
            spell_issues = [i for i in review_results["issues_found"]
                          if i["type"].startswith("spelling_grammar")]
            summary_parts.append(f"Spelling/Grammar: {len(spell_issues)} issues found")

        if review_results["fact_check_performed"]:
            accuracy_score = review_results["accuracy_score"]
            summary_parts.append(f"Factual Accuracy: {accuracy_score:.1%}")

            factual_errors = [i for i in review_results["issues_found"]
                            if i["type"] == "factual_error"]
            outdated = [i for i in review_results["issues_found"]
                       if i["type"] == "outdated_info"]
            unsupported = [i for i in review_results["issues_found"]
                          if i["type"] == "unsupported_claim"]

            if factual_errors:
                summary_parts.append(f"  - Factual errors: {len(factual_errors)}")
            if outdated:
                summary_parts.append(f"  - Outdated info: {len(outdated)}")
            if unsupported:
                summary_parts.append(f"  - Unsupported claims: {len(unsupported)}")

        summary_parts.append(f"\nTotal issues found: {total_issues}")
        summary_parts.append(f"Corrections applied: {total_corrections}")

        if total_issues == 0:
            summary_parts.append("\n✓ Content passed review with no issues!")
        elif total_corrections > 0:
            summary_parts.append(f"\n✓ {total_corrections} corrections have been applied")
        else:
            summary_parts.append(f"\n⚠ Manual review recommended for {total_issues} issues")

        return "\n".join(summary_parts)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response.

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be extracted
        """
        import json
        import re

        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fence
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

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data.

        Args:
            input_data: Input data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        await super().validate_input(input_data)

        if "content" not in input_data:
            raise ValueError("Input must contain 'content' field")

        if not isinstance(input_data["content"], str):
            raise ValueError("Content must be a string")

        if len(input_data["content"].strip()) == 0:
            raise ValueError("Content cannot be empty")

        return True

    async def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data.

        Args:
            output_data: Output data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        await super().validate_output(output_data)

        required_fields = [
            "original_content",
            "reviewed_content",
            "issues_found",
            "corrections_applied",
            "review_summary"
        ]

        for field in required_fields:
            if field not in output_data:
                raise ValueError(f"Output missing required field: {field}")

        return True
