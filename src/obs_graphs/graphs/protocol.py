"""Protocol definitions for workflow graphs."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.obs_graphs.api.schemas import WorkflowRunRequest
    from src.obs_graphs.graphs.article_proposal.graph import WorkflowResult


class WorkflowGraphProtocol(Protocol):
    """Protocol for workflow graph implementations."""

    async def run_workflow(self, request: "WorkflowRunRequest") -> "WorkflowResult":
        """
        Execute a workflow from start to finish.

        Args:
            request: Workflow run request with prompts and configuration

        Returns:
            WorkflowResult with execution results
        """
        ...
