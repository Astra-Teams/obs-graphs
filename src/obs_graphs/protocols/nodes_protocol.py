"""Protocol definition for node interface."""

from typing import Protocol

from src.obs_graphs.graphs.article_proposal.state import NodeResult


class NodeProtocol(Protocol):
    """Protocol for node operations."""

    name: str  # Class attribute for node name

    def execute(self, context: dict) -> NodeResult:
        """
        Execute the node's task.

        Args:
            context: Dictionary containing execution context including:
                - branch_name: Branch to operate on
                - vault_summary: Summary of vault state
                - strategy: Workflow strategy
                - prompt: User prompt (if any)
                - previous_changes: FileChanges from previous nodes
                - previous_results: Results from previous nodes

        Returns:
            NodeResult containing success status, file changes, and metadata

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
