"""Base agent interface and common utilities for Obsidian Vault agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class FileAction(Enum):
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
class AgentResult:
    """
    Result returned by agent execution.

    Attributes:
        success: Whether the agent execution completed successfully
        changes: List of file changes to apply to the vault
        message: Human-readable description of what the agent did
        metadata: Additional information about the execution (e.g., metrics, warnings)
    """

    success: bool
    changes: list[FileChange]
    message: str
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all Obsidian Vault agents.

    All agents must implement the execute method to perform their specific tasks
    on the vault. Agents should be stateless and idempotent where possible.
    """

    @abstractmethod
    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        """
        Execute the agent's task on the vault.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing execution context (e.g., vault summary, previous results)

        Returns:
            AgentResult containing success status, file changes, and metadata

        Raises:
            ValueError: If input validation fails
            Exception: For unexpected errors during execution
        """
        pass

    @abstractmethod
    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information for this agent.

        Args:
            context: Execution context dictionary

        Returns:
            True if context is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this agent.

        Returns:
            Human-readable agent name
        """
        pass
