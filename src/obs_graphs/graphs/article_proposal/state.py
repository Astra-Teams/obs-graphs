"""Shared state definitions for the Obsidian Vault workflow graph."""

from enum import Enum

# Re-export Pydantic models for backward compatibility
from src.obs_graphs.graphs.article_proposal.schemas import (
    FileAction,
    FileChange,
    GraphStateModel,
    NodeResult,
    NodeResultModel,
    VaultSummary,
)


class WorkflowStrategy(str, Enum):
    """Enumeration of available workflow strategies."""

    RESEARCH_PROPOSAL = "research_proposal"


class WorkflowStatus(str, Enum):
    """Enumeration of workflow execution statuses."""

    CONTINUE = "continue"
    FINISH = "finish"


class GraphState(GraphStateModel):
    """State passed between nodes in the workflow graph."""

    pass
    """State passed between nodes in the workflow graph."""
    pass


__all__ = [
    "WorkflowStrategy",
    "WorkflowStatus",
    "FileAction",
    "FileChange",
    "NodeResult",
    "VaultSummary",
    "GraphState",
    "NodeResultModel",
    "GraphStateModel",
]
