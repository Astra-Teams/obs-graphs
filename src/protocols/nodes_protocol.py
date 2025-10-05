"""Protocol definition for node/agent interface."""

from pathlib import Path
from typing import Protocol

from src.state import AgentResult


class NodeProtocol(Protocol):
    """Protocol for node/agent operations."""

    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        """
        Execute the node's task on the vault.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing execution context (e.g., vault summary, previous results)

        Returns:
            AgentResult containing success status, file changes, and metadata

        Raises:
            ValueError: If input validation fails
            Exception: For unexpected errors during execution
        """
        ...

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information for this node.

        Args:
            context: Execution context dictionary

        Returns:
            True if context is valid, False otherwise
        """
        ...

    def get_name(self) -> str:
        """
        Get the name of this node.

        Returns:
            Human-readable node name
        """
        ...
