"""Communication protocol for agent-to-agent data exchange."""

from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMessage(BaseModel):
    """Message passed between agents."""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: AgentStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchResultsMessage(BaseModel):
    """Message format for search results from PostSearcher."""
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    selected_count: int
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": self.results,
            "total_found": self.total_found,
            "selected_count": self.selected_count,
            "timestamp": self.timestamp.isoformat()
        }


class BlogPlanMessage(BaseModel):
    """Message format for blog plan from BlogPlanner."""
    title: str
    sections: List[Dict[str, Any]]
    key_points: List[str]
    target_length: int
    sources_analyzed: int
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "sections": self.sections,
            "key_points": self.key_points,
            "target_length": self.target_length,
            "sources_analyzed": self.sources_analyzed,
            "timestamp": self.timestamp.isoformat()
        }


class BlogContentMessage(BaseModel):
    """Message format for final blog content from BlogWriter."""
    title: str
    content: str
    word_count: int
    sections_count: int
    tone_applied: bool
    sources: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "sections_count": self.sections_count,
            "tone_applied": self.tone_applied,
            "sources": self.sources,
            "timestamp": self.timestamp.isoformat()
        }


class CheckpointData(BaseModel):
    """Checkpoint data for resuming workflow."""
    workflow_id: str
    current_step: str
    completed_steps: List[str]
    search_results_file: Optional[str] = None
    blog_plan_file: Optional[str] = None
    blog_content_file: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "search_results_file": self.search_results_file,
            "blog_plan_file": self.blog_plan_file,
            "blog_content_file": self.blog_content_file,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
