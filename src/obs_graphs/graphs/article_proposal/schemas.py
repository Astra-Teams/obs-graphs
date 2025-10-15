"""Pydantic models for article proposal graph schemas."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Dict, List, TypedDict, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


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


class VaultSummary(BaseModel):
    """
    Pydantic model representing a summary of the vault's state.

    Attributes:
        total_articles: Total number of markdown files in the vault.
    """

    total_articles: int


class NodeResultModel(BaseModel):
    """Pydantic model for node execution results."""

    success: bool
    changes: List[FileChange]
    message: str
    metadata: Dict = {}


class GraphStateModel(TypedDict):
    """TypedDict for graph state used by LangGraph."""

    vault_summary: VaultSummary
    strategy: str
    prompts: List[str]
    accumulated_changes: List[FileChange]
    node_results: Dict
    messages: Annotated[List[str], "add_messages"]
