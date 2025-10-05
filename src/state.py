"""Shared state definitions for the Obsidian Vault workflow graph."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, TypedDict


class FileAction(str, Enum):
    """Enum representing file operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class FileChange:
    """Represents a file change to be applied to the vault."""

    path: str
    action: FileAction
    content: Optional[str] = None

    def __post_init__(self) -> None:
        if (
            self.action in (FileAction.CREATE, FileAction.UPDATE)
            and self.content is None
        ):
            raise ValueError(f"Content must be provided for {self.action.value} action")
        if self.action == FileAction.DELETE and self.content is not None:
            raise ValueError("Content should not be provided for DELETE action")


@dataclass
class AgentResult:
    """Result returned by node execution."""

    success: bool
    changes: List[FileChange]
    message: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class VaultSummary:
    """Dataclass representing a summary of the vault's state."""

    total_articles: int
    categories: List[str]
    recent_updates: List[str]


class GraphState(TypedDict, total=False):
    """State passed between nodes in the workflow graph."""

    vault_path: Path
    requested_category: Optional[str]
    available_categories: List[str]
    selected_category: Optional[str]
    category_content: str
    keywords: List[str]
    existing_titles: List[str]
    themes: List[str]
    selected_theme: Optional[str]
    report_markdown: str
    pull_request: Dict[str, str]
    agent_results: Dict[str, Dict]
    messages: List[str]
