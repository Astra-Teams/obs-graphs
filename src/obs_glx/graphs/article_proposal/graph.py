"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

from dataclasses import dataclass, field

from langgraph.graph import END, StateGraph

from src.obs_glx.api.schemas import WorkflowRunRequest
from src.obs_glx.graphs.article_proposal.state import (
    FileChange,
    GraphState,
    NodeResult,
    WorkflowStrategy,
)
from src.obs_glx.protocols import (
    NodeProtocol,
    VaultServiceProtocol,
)


@dataclass
class WorkflowPlan:
    """
    Plan for workflow execution.

    Attributes:
        nodes: Ordered list of node names to execute
        strategy: Workflow strategy identifier
    """

    nodes: list[str]
    strategy: str


@dataclass
class WorkflowResult:
    """
    Result of workflow execution.

    Attributes:
        success: Whether the workflow completed successfully
        changes: Aggregated list of all file changes from nodes
        summary: Human-readable summary of what was done
        node_results: Dictionary mapping node names to their results
        branch_name: Name of the branch registered in GitHub
    """

    success: bool
    changes: list[FileChange]
    summary: str
    node_results: dict = field(default_factory=dict)
    branch_name: str = ""


class ArticleProposalGraph:
    """
    Builds and orchestrates the execution of nodes using LangGraph.

    This class analyzes the vault to determine which nodes should run,
    then executes them in the appropriate order using a state graph.
    """

    def __init__(
        self,
        vault_service: VaultServiceProtocol,
        article_proposal_node: NodeProtocol,
        deep_research_node: NodeProtocol,
        submit_draft_branch_node: NodeProtocol,
    ):
        """
        Initialize the ArticleProposalGraph with required dependencies.

        Args:
            vault_service: Service for vault file operations
            article_proposal_node: Node for article proposal generation
            deep_research_node: Node for deep research operations
            submit_draft_branch_node: Node for submitting draft branches
        """
        self.vault_service = vault_service
        self._nodes = {
            "article_proposal": article_proposal_node,
            "deep_research": deep_research_node,
            "submit_draft_branch": submit_draft_branch_node,
        }

    def _get_node(self, node_name: str) -> NodeProtocol:
        """
        Get a node instance by name.

        Args:
            node_name: Name of the node to retrieve

        Returns:
            NodeProtocol instance for the specified node

        Raises:
            ValueError: If node_name is unknown
        """
        if node_name not in self._nodes:
            raise ValueError(f"Unknown node: {node_name}")

        return self._nodes[node_name]

    async def run_workflow(self, request: WorkflowRunRequest) -> WorkflowResult:
        """
        Run the complete workflow: execute nodes and submit the draft via GitHub.

        Args:
            request: Workflow run request with optional strategy override

        Returns:
            WorkflowResult with execution results
        """

        try:
            # Analyze vault to create workflow plan
            workflow_plan = self.get_default_plan(request)

            # Override strategy if specified in request
            if request.strategy:
                workflow_plan.strategy = request.strategy

            # Execute workflow
            workflow_result = await self._run_graph(
                workflow_plan,
                prompts=request.prompts,
            )

            if not workflow_result.success:
                raise Exception(f"Workflow execution failed: {workflow_result.summary}")

            branch_result = workflow_result.node_results.get("submit_draft_branch", {})
            branch_metadata = branch_result.get("metadata", {})
            workflow_result.branch_name = branch_metadata.get("branch_name", "")

            return workflow_result

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                node_results={},
            )

    def get_default_plan(
        self,
        request: WorkflowRunRequest,
    ) -> WorkflowPlan:
        """
        Return the default static workflow plan.

        Note: This currently returns a fixed plan. If dynamic plan determination
        is needed in the future, replace this implementation with analysis logic.
        """
        strategy = WorkflowStrategy.RESEARCH_PROPOSAL.value
        nodes = [
            "article_proposal",
            "deep_research",
            "submit_draft_branch",
        ]

        return WorkflowPlan(nodes=nodes, strategy=strategy)

    async def _run_graph(
        self,
        workflow_plan: WorkflowPlan,
        prompts: list[str] | None = None,
    ) -> WorkflowResult:
        """
        Run the compiled LangGraph using the provided workflow plan.

        This method intentionally lets exceptions propagate to the caller so
        that a single responsibility for error handling remains in `run_workflow`.
        """
        # Initialize workflow state
        vault_summary = self.vault_service.get_vault_summary()

        prompt_list = prompts or []

        initial_state: GraphState = {
            "vault_summary": vault_summary,
            "strategy": workflow_plan.strategy,
            "prompts": prompt_list,
            "accumulated_changes": [],
            "node_results": {},
            "messages": [],
        }

        # Build state graph based on workflow plan
        graph = self._build_graph(workflow_plan)

        # Execute the workflow; let exceptions bubble up to caller
        final_state = await graph.ainvoke(initial_state)

        # Extract results from final state
        all_changes = final_state["accumulated_changes"]
        node_results = final_state["node_results"]

        # Generate summary
        summary = self._generate_summary(node_results, workflow_plan.strategy)

        return WorkflowResult(
            success=True,
            changes=all_changes,
            summary=summary,
            node_results=node_results,
        )

    def _build_graph(self, workflow_plan: WorkflowPlan) -> StateGraph:
        """
        Build LangGraph state graph based on workflow plan.

        Args:
            workflow_plan: Plan specifying node execution order

        Returns:
            Configured StateGraph ready for execution
        """
        # Create state graph
        workflow = StateGraph(GraphState)

        # Add node nodes
        for node_name in workflow_plan.nodes:
            workflow.add_node(node_name, self._create_node_node(node_name))

        # Add edges to create sequential execution
        workflow.set_entry_point(workflow_plan.nodes[0])

        for i in range(len(workflow_plan.nodes) - 1):
            current_node = workflow_plan.nodes[i]
            next_node = workflow_plan.nodes[i + 1]
            workflow.add_edge(current_node, next_node)

        # Last node leads to END
        workflow.add_edge(workflow_plan.nodes[-1], END)

        return workflow.compile()

    def _create_node_node(self, node_name: str):
        """
        Create a node function for the specified node.

        Args:
            node_name: Name of the node to create node for

        Returns:
            Callable node function for use in state graph
        """

        async def node_node(state: GraphState) -> GraphState:
            """Execute the node and update state."""
            node = self._get_node(node_name)

            # Execute node with the graph state directly (avoid redundant copy)
            result: NodeResult = await node.execute(state)

            # Check if node failed and raise exception to stop workflow
            if not result.success:
                raise Exception(f"Node {node_name} failed: {result.message}")

            # Update state with results
            state["accumulated_changes"].extend(result.changes)
            state["node_results"][node_name] = {
                "success": result.success,
                "message": result.message,
                "changes_count": len(result.changes),
                "metadata": result.metadata,
            }
            state["messages"].append(
                f"{node_name}: {result.message} ({len(result.changes)} changes)"
            )

            # Merge node metadata into state for downstream nodes
            if result.metadata:
                # Update state in place
                for key, value in result.metadata.items():
                    state[key] = value

            return state

        return node_node

    def _generate_summary(self, node_results: dict, strategy: str) -> str:
        """
        Generate human-readable summary of workflow execution.

        Args:
            node_results: Results from all executed nodes
            strategy: Workflow strategy that was used

        Returns:
            Summary string
        """
        successful_nodes = [
            name for name, result in node_results.items() if result["success"]
        ]
        total_changes = sum(result["changes_count"] for result in node_results.values())

        summary_parts = [
            f"Workflow completed with '{strategy}' strategy.",
            f"Executed {len(successful_nodes)}/{len(node_results)} nodes successfully.",
            f"Total changes: {total_changes} file operations.",
        ]

        # Add node-specific details
        for node_name, result in node_results.items():
            if result["success"]:
                summary_parts.append(f"- {node_name}: {result['message']}")

        return "\n".join(summary_parts)
