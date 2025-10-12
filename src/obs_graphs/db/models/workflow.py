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

from src.obs_graphs.db.database import Base


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
    prompt = Column(Text, nullable=True)
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
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self):
        prompt_preview = (
            f"{self.prompt[:50]}..."
            if self.prompt and len(self.prompt) > 50
            else self.prompt
        )
        return f"<Workflow(id={self.id}, status={self.status.value}, strategy={self.strategy}, prompt={prompt_preview!r})>"
