"""Default implementations mixin for agents (similar to Swift's protocol extension)."""

from pathlib import Path
from typing import List, Optional

from src.state import AgentResult, FileChange


class AgentDefaultsMixin:
    """
    Mixin providing default implementations and utility methods for agents.

    Similar to Swift's protocol extensions, this mixin provides default
    implementations that can be overridden by concrete agents.
    """

    def validate_input(self, context: dict) -> bool:
        """
        Default validation that accepts any context.

        Override this method in concrete agents that need specific validation.

        Args:
            context: Execution context dictionary

        Returns:
            True by default
        """
        _ = context  # context is intentionally unused in default implementation
        return True

    def _validate_vault_path(self, vault_path: Path) -> bool:
        """
        Validate that the vault path exists and is a directory.

        Args:
            vault_path: Path to validate

        Returns:
            True if path exists and is a directory
        """
        return vault_path.exists() and vault_path.is_dir()

    def _create_success_result(
        self,
        message: str,
        changes: Optional[List[FileChange]] = None,
        metadata: Optional[dict] = None,
    ) -> AgentResult:
        """
        Create a successful AgentResult.

        Args:
            message: Success message
            changes: List of file changes (defaults to empty list)
            metadata: Additional metadata (defaults to empty dict)

        Returns:
            AgentResult with success=True
        """
        return AgentResult(
            success=True,
            changes=changes or [],
            message=message,
            metadata=metadata or {},
        )

    def _create_failure_result(
        self,
        message: str,
        error: Optional[Exception] = None,
        metadata: Optional[dict] = None,
    ) -> AgentResult:
        """
        Create a failed AgentResult.

        Args:
            message: Failure message
            error: Optional exception that caused the failure
            metadata: Additional metadata (defaults to empty dict)

        Returns:
            AgentResult with success=False
        """
        result_metadata = metadata or {}
        if error:
            result_metadata["error"] = str(error)
            result_metadata["error_type"] = type(error).__name__

        return AgentResult(
            success=False, changes=[], message=message, metadata=result_metadata
        )

    def _safe_execute(self, vault_path: Path, context: dict) -> AgentResult:
        """
        Wrapper around execute() that handles common errors gracefully.

        This method validates the vault path and catches exceptions.
        Concrete agents should implement execute() instead of overriding this.

        Args:
            vault_path: Path to the Obsidian Vault
            context: Execution context

        Returns:
            AgentResult from execute() or error result
        """
        # Validate vault path
        if not self._validate_vault_path(vault_path):
            return self._create_failure_result(
                f"Vault path does not exist or is not a directory: {vault_path}",
                metadata={"vault_path": str(vault_path)},
            )

        # Validate input context
        if not self.validate_input(context):
            return self._create_failure_result(
                "Invalid execution context provided",
                metadata={"context_keys": list(context.keys())},
            )

        # Execute the agent's task
        try:
            # This calls the concrete agent's execute method
            return self.execute(vault_path, context)  # type: ignore
        except Exception as e:
            return self._create_failure_result(
                f"Unexpected error during execution: {str(e)}",
                error=e,
            )
