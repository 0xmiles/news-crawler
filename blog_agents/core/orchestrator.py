"""Orchestrator for coordinating blog generation workflow."""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from blog_agents.config.agent_config import Config, get_config
from blog_agents.agents.post_searcher import PostSearcher
from blog_agents.agents.blog_planner import BlogPlanner
from blog_agents.agents.blog_writer import BlogWriter
from blog_agents.agents.blog_reviewer import BlogReviewer
from blog_agents.utils.file_manager import FileManager
from blog_agents.core.communication import CheckpointData, AgentStatus

logger = logging.getLogger(__name__)


class BlogOrchestrator:
    """Orchestrator for multi-agent blog generation workflow."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize orchestrator.

        Args:
            config: System configuration (loads from default if None)
        """
        self.config = config or get_config()

        # Initialize agents
        self.post_searcher = PostSearcher(self.config)
        self.blog_planner = BlogPlanner(self.config)
        self.blog_writer = BlogWriter(self.config)
        self.blog_reviewer = BlogReviewer(self.config)

        # File manager
        self.file_manager = FileManager(self.config.blog_agents.output_dir)

        # Workflow state
        self.workflow_id: Optional[str] = None
        self.current_step: Optional[str] = None
        self.completed_steps: list[str] = []

    async def generate_blog(
        self,
        keywords: str,
        resume_from: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate blog post from keywords.

        Args:
            keywords: Search keywords/topic
            resume_from: Optional workflow ID to resume from

        Returns:
            Dictionary with generation results

        Raises:
            Exception: If generation fails
        """
        # Initialize or resume workflow
        if resume_from:
            logger.info(f"Resuming workflow: {resume_from}")
            await self._resume_workflow(resume_from)
        else:
            self.workflow_id = str(uuid.uuid4())
            self.completed_steps = []
            logger.info(f"Starting new workflow: {self.workflow_id}")

        try:
            # Step 1: Search for articles
            if "search" not in self.completed_steps:
                logger.info("Step 1: Searching for articles")
                self.current_step = "search"
                await self._save_checkpoint()

                search_result = await self.post_searcher.run({"keywords": keywords})

                if search_result.status != AgentStatus.COMPLETED:
                    raise Exception(f"PostSearcher failed: {search_result.error}")

                self.completed_steps.append("search")
                await self._save_checkpoint()
                logger.info("✓ Search completed")
            else:
                logger.info("✓ Search already completed (resuming)")

            # Step 2: Plan blog post
            if "plan" not in self.completed_steps:
                logger.info("Step 2: Planning blog post")
                self.current_step = "plan"
                await self._save_checkpoint()

                # Load search results
                search_data = await self.file_manager.read_json("search_results.json")
                if not search_data:
                    raise Exception("Search results not found")

                plan_result = await self.blog_planner.run({
                    "query": search_data.get("query", keywords),
                    "selected_articles": search_data.get("selected_articles", [])
                })

                if plan_result.status != AgentStatus.COMPLETED:
                    raise Exception(f"BlogPlanner failed: {plan_result.error}")

                self.completed_steps.append("plan")
                await self._save_checkpoint()
                logger.info("✓ Planning completed")
            else:
                logger.info("✓ Planning already completed (resuming)")

            # Step 3: Write blog post
            if "write" not in self.completed_steps:
                logger.info("Step 3: Writing blog post")
                self.current_step = "write"
                await self._save_checkpoint()

                # Load blog plan
                plan_data = await self.file_manager.read_json("blog_plan.json")
                if not plan_data:
                    raise Exception("Blog plan not found")

                write_result = await self.blog_writer.run(plan_data)

                if write_result.status != AgentStatus.COMPLETED:
                    raise Exception(f"BlogWriter failed: {write_result.error}")

                self.completed_steps.append("write")
                await self._save_checkpoint()
                logger.info("✓ Writing completed")
            else:
                logger.info("✓ Writing already completed (resuming)")

            # Step 4: Review blog post
            if "review" not in self.completed_steps:
                logger.info("Step 4: Reviewing blog post")
                self.current_step = "review"
                await self._save_checkpoint()

                # Load written blog from write_result or search_data
                search_data = await self.file_manager.read_json("search_results.json")
                if not search_data:
                    raise Exception("Search results not found")

                # Get the most recent write result
                if "write" in self.completed_steps:
                    # Load blog plan to get title and sources
                    plan_data = await self.file_manager.read_json("blog_plan.json")
                    if not plan_data:
                        raise Exception("Blog plan not found")

                    # Read the written blog file
                    blog_filename = write_result.data.get("filename")
                    blog_content = await self.file_manager.read_text(blog_filename)

                    review_input = {
                        "title": plan_data.get("title", ""),
                        "content": blog_content,
                        "sources": plan_data.get("sources", []),
                        "filename": blog_filename
                    }

                    review_result = await self.blog_reviewer.run(review_input)

                    if review_result.status != AgentStatus.COMPLETED:
                        raise Exception(f"BlogReviewer failed: {review_result.error}")

                    self.completed_steps.append("review")
                    await self._save_checkpoint()
                    logger.info("✓ Review completed")
            else:
                logger.info("✓ Review already completed (resuming)")

            # Mark workflow as complete
            self.current_step = "completed"
            await self._save_checkpoint()

            # Prepare final result
            result = {
                "workflow_id": self.workflow_id,
                "status": "completed",
                "search_results": await self.file_manager.read_json("search_results.json"),
                "blog_plan": await self.file_manager.read_json("blog_plan.json"),
                "review_report": await self.file_manager.read_json("review_report.json"),
                "blog_file": write_result.data.get("filename"),
                "word_count": write_result.data.get("word_count"),
                "sections_count": write_result.data.get("sections_count"),
                "completed_at": datetime.now().isoformat()
            }

            logger.info(f"✓ Blog generation completed: {result['blog_file']}")
            return result

        except Exception as e:
            logger.error(f"Blog generation failed: {e}")
            self.current_step = "failed"
            await self._save_checkpoint()
            raise

    async def _save_checkpoint(self):
        """Save workflow checkpoint."""
        checkpoint = CheckpointData(
            workflow_id=self.workflow_id,
            current_step=self.current_step,
            completed_steps=self.completed_steps,
            search_results_file="search_results.json" if "search" in self.completed_steps else None,
            blog_plan_file="blog_plan.json" if "plan" in self.completed_steps else None,
            review_report_file="review_report.json" if "review" in self.completed_steps else None,
            metadata={
                "last_updated": datetime.now().isoformat()
            }
        )

        checkpoint_file = f"checkpoint_{self.workflow_id}.json"
        await self.file_manager.write_json(checkpoint_file, checkpoint.to_dict())
        logger.debug(f"Checkpoint saved: {checkpoint_file}")

    async def _resume_workflow(self, workflow_id: str):
        """Resume workflow from checkpoint.

        Args:
            workflow_id: Workflow ID to resume

        Raises:
            FileNotFoundError: If checkpoint not found
        """
        checkpoint_file = f"checkpoint_{workflow_id}.json"
        checkpoint_data = await self.file_manager.read_json(checkpoint_file)

        if not checkpoint_data:
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_file}")

        self.workflow_id = checkpoint_data["workflow_id"]
        self.current_step = checkpoint_data["current_step"]
        self.completed_steps = checkpoint_data["completed_steps"]

        logger.info(f"Resumed workflow from step: {self.current_step}")
        logger.info(f"Completed steps: {self.completed_steps}")

    async def search_only(self, keywords: str) -> Dict[str, Any]:
        """Execute only the search step.

        Args:
            keywords: Search keywords

        Returns:
            Search results
        """
        logger.info(f"Executing search only: {keywords}")

        search_result = await self.post_searcher.run({"keywords": keywords})

        if search_result.status != AgentStatus.COMPLETED:
            raise Exception(f"Search failed: {search_result.error}")

        return search_result.data

    async def plan_only(self, search_results_file: str = "search_results.json") -> Dict[str, Any]:
        """Execute only the planning step.

        Args:
            search_results_file: Path to search results file

        Returns:
            Blog plan
        """
        logger.info("Executing planning only")

        # Load search results
        search_data = await self.file_manager.read_json(search_results_file)
        if not search_data:
            raise FileNotFoundError(f"Search results not found: {search_results_file}")

        plan_result = await self.blog_planner.run({
            "query": search_data.get("query", ""),
            "selected_articles": search_data.get("selected_articles", [])
        })

        if plan_result.status != AgentStatus.COMPLETED:
            raise Exception(f"Planning failed: {plan_result.error}")

        return plan_result.data

    async def write_only(self, plan_file: str = "blog_plan.json") -> Dict[str, Any]:
        """Execute only the writing step.

        Args:
            plan_file: Path to blog plan file

        Returns:
            Blog content metadata
        """
        logger.info("Executing writing only")

        # Load blog plan
        plan_data = await self.file_manager.read_json(plan_file)
        if not plan_data:
            raise FileNotFoundError(f"Blog plan not found: {plan_file}")

        write_result = await self.blog_writer.run(plan_data)

        if write_result.status != AgentStatus.COMPLETED:
            raise Exception(f"Writing failed: {write_result.error}")

        return write_result.data

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status.

        Returns:
            Workflow status information
        """
        return {
            "workflow_id": self.workflow_id,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "total_steps": 4,
            "progress_percentage": (len(self.completed_steps) / 4) * 100
        }
