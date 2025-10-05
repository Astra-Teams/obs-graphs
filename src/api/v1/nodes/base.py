"""Base agent interface and common utilities for Obsidian Vault agents."""

from abc import ABC, abstractmethod
from pathlib import Path

from src.protocols import NodeProtocol
from src.state import AgentResult


class BaseAgent(ABC, NodeProtocol):
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
