# src/db/models/workflow.py
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)

from src.obs_glx.db.database import Base


class WorkflowStatus(enum.Enum):
    """Enum for workflow execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Workflow(Base):
    """
    Database model for workflow tracking.

    Tracks the lifecycle of automated Obsidian Vault improvement workflows,
    from initial trigger to PR creation or failure.
    """

    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    workflow_type = Column(
        String(50), nullable=False, default="article-proposal", index=True
    )
    prompt = Column(JSON, nullable=True)
    status = Column(
        Enum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.PENDING,
        index=True,
    )
    strategy = Column(String(100), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    branch_name = Column("pr_url", String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    workflow_metadata = Column(JSON, nullable=True)
    progress_message = Column(String(500), nullable=True)
    progress_percent = Column(Integer, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self):
        # Handle prompt as either list or legacy string
        if isinstance(self.prompt, list):
            first_prompt = self.prompt[0] if self.prompt else ""
            prompt_preview = (
                f"{first_prompt[:50]}..."
                if first_prompt and len(first_prompt) > 50
                else first_prompt
            )
        else:
            prompt_preview = (
                f"{self.prompt[:50]}..."
                if self.prompt and len(self.prompt) > 50
                else self.prompt
            )
        return f"<Workflow(id={self.id}, type={self.workflow_type}, status={self.status.value}, strategy={self.strategy}, prompt={prompt_preview!r})>"
