"""Protocol definition for node interface."""

from typing import Protocol

from src.obs_glx.graphs.article_proposal.state import GraphState, NodeResult


class NodeProtocol(Protocol):
    """Protocol for node operations."""

    name: str  # Class attribute for node name

    async def execute(self, state: GraphState) -> NodeResult:
        """
        Execute the node's task.

        Args:
            state: GraphState containing execution context including:
                - vault_summary: Summary of vault state
                - strategy: Workflow strategy
                - prompts: User prompts (if any)
                - accumulated_changes: FileChanges from previous nodes
                - node_results: Results from previous nodes

        Returns:
            NodeResult containing success status, file changes, and metadata

        Raises:
            ValueError: If input validation fails
            Exception: For unexpected errors during execution
        """
        ...

    def validate_input(self, state: GraphState) -> bool:
        """
        Validate that the context contains required information for this node.

        Args:
            state: Execution context dictionary

        Returns:
            True if context is valid, False otherwise
        """
        ...
