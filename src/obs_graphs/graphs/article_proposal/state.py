"""Shared state definitions for the Obsidian Vault workflow graph."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Dict, List, Optional, TypedDict

# Re-export Pydantic models for backward compatibility
from src.obs_graphs.graphs.article_proposal.schemas import (
    GraphStateModel,
    NodeResultModel,
    VaultSummaryModel,
)


class WorkflowStrategy(str, Enum):
    """Enumeration of available workflow strategies."""

    RESEARCH_PROPOSAL = "research_proposal"


class FileAction(str, Enum):
    """Enum representing file operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class FileChange:
    """
    Represents a file change to be applied to the vault.

    Attributes:
        path: Relative path to the file within the vault
        action: Type of operation (CREATE, UPDATE, DELETE)
        content: New content for the file (required for CREATE/UPDATE, None for DELETE)
    """

    path: str
    action: FileAction
    content: Optional[str] = None

    def __post_init__(self):
        """Validate that content is provided for CREATE and UPDATE actions."""
        if (
            self.action in (FileAction.CREATE, FileAction.UPDATE)
            and self.content is None
        ):
            raise ValueError(f"Content must be provided for {self.action.value} action")
        if self.action == FileAction.DELETE and self.content is not None:
            raise ValueError("Content should not be provided for DELETE action")


@dataclass
class NodeResult:
    """
    Result returned by node execution.

    Attributes:
        success: Whether the node execution completed successfully
        changes: List of file changes to apply to the vault
        message: Human-readable description of what the node did
        metadata: Additional information about the execution (e.g., metrics, warnings)
    """

    success: bool
    changes: List[FileChange]
    message: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class VaultSummary:
    """
    Dataclass representing a summary of the vault's state.

    Attributes:
        total_articles: Total number of markdown files in the vault.
        categories: List of top-level directories representing categories.
        recent_updates: List of recently modified files.
    """

    total_articles: int
    categories: List[str]
    recent_updates: List[str]


class GraphState(TypedDict):
    """State passed between nodes in the workflow graph."""

    vault_summary: VaultSummary
    strategy: str
    prompts: List[str]
    backend: str
    accumulated_changes: List[FileChange]
    node_results: Dict
    messages: Annotated[List, "add_messages"]


__all__ = [
    "WorkflowStrategy",
    "FileAction",
    "FileChange",
    "NodeResult",
    "VaultSummary",
    "GraphState",
    "VaultSummaryModel",
    "NodeResultModel",
    "GraphStateModel",
]
