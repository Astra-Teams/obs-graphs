"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

from dataclasses import dataclass, field
from typing import Callable

from langgraph.graph import END, StateGraph
from obs_gtwy_sdk import GatewayClientProtocol
from olm_d_rch_sdk import ResearchClientProtocol

from src.obs_graphs.api.schemas import WorkflowRunRequest
from src.obs_graphs.config import obs_graphs_settings
from src.obs_graphs.graphs.article_proposal.state import (
    NodeResult,
    FileChange,
    GraphState,
    WorkflowStrategy,
)
from src.obs_graphs.protocols import (
    LLMClientProtocol,
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
        branch_name: Name of the branch registered by obs-gtwy
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
        llm_client_provider: Callable[[str | None], LLMClientProtocol],
        gateway_client: GatewayClientProtocol,
        research_client: ResearchClientProtocol,
    ):
        """
        Initialize the ArticleProposalGraph with required dependencies.

        Args:
            vault_service: Service for vault file operations
            llm_client_provider: Provider function for creating LLM clients
            gateway_client: Client for Obsidian gateway operations
            research_client: Client for deep research operations
        """
        self.vault_service = vault_service
        self.llm_client_provider = llm_client_provider
        self.gateway_client = gateway_client
        self.research_client = research_client

        # Initialize nodes
        self._nodes: dict[str, NodeProtocol] = {}

    def _get_node(self, node_name: str) -> NodeProtocol:
        """
        Get or create a node instance by name.

        Args:
            node_name: Name of the node to retrieve

        Returns:
            NodeProtocol instance for the specified node

        Raises:
            ValueError: If node_name is unknown
        """
        if node_name not in self._nodes:
            if node_name == "article_proposal":
                from src.obs_graphs.graphs.article_proposal.nodes.node1_article_proposal import (
                    ArticleProposalNode,
                )

                self._nodes[node_name] = ArticleProposalNode(self.llm_client_provider)
            elif node_name == "deep_research":
                from src.obs_graphs.graphs.article_proposal.nodes.node2_deep_research import (
                    DeepResearchNode,
                )

                self._nodes[node_name] = DeepResearchNode(self.research_client)
            elif node_name == "submit_pull_request":
                from src.obs_graphs.graphs.article_proposal.nodes.node3_submit_pull_request import (
                    SubmitPullRequestNode,
                )

                self._nodes[node_name] = SubmitPullRequestNode(self.gateway_client)
            else:
                raise ValueError(f"Unknown node: {node_name}")

        return self._nodes[node_name]

    def run_workflow(self, request: WorkflowRunRequest) -> WorkflowResult:
        """
        Run the complete workflow: execute nodes and submit the draft via obs-gtwy.

        Args:
            request: Workflow run request with optional strategy override

        Returns:
            WorkflowResult with execution results
        """

        try:
            # Analyze vault to create workflow plan
            workflow_plan = self.determine_workflow_plan(request)

            # Override strategy if specified in request
            if request.strategy:
                workflow_plan.strategy = request.strategy

            # Execute workflow
            workflow_result = self.execute_workflow(
                workflow_plan,
                prompts=request.prompts,
                backend=request.backend,
            )

            if not workflow_result.success:
                raise Exception(f"Workflow execution failed: {workflow_result.summary}")

            pr_result = workflow_result.node_results.get("submit_pull_request", {})
            pr_metadata = pr_result.get("metadata", {})
            workflow_result.branch_name = pr_metadata.get("branch_name", "")

            return workflow_result

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                node_results={},
            )

    def determine_workflow_plan(
        self,
        request: WorkflowRunRequest,
    ) -> WorkflowPlan:
        """
        Analyze vault and request to determine which nodes to run and in what order.

        The workflow now requires a prompt and always uses the research_proposal strategy.

        Args:
            request: Workflow run request

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        strategy = WorkflowStrategy.RESEARCH_PROPOSAL.value
        nodes = [
            "article_proposal",
            "deep_research",
            "submit_pull_request",
        ]

        return WorkflowPlan(nodes=nodes, strategy=strategy)

    def execute_workflow(
        self,
        workflow_plan: WorkflowPlan,
        prompts: list[str] | None = None,
        backend: str | None = None,
    ) -> WorkflowResult:
        """
        Execute workflow using LangGraph state graph.

        Args:
            workflow_plan: Plan specifying which nodes to run
            prompts: User prompts for research workflows (list of strings)
            backend: Backend LLM to use

        Returns:
            WorkflowResult with aggregated changes and results
        """
        # Initialize workflow state
        vault_summary = self.vault_service.get_vault_summary()

        selected_backend = (backend or obs_graphs_settings.llm_backend).strip().lower()

        prompt_list = prompts or []

        initial_state: GraphState = {
            "vault_summary": vault_summary,
            "strategy": workflow_plan.strategy,
            "prompts": prompt_list,
            "backend": selected_backend,
            "accumulated_changes": [],
            "node_results": {},
            "messages": [],
        }

        # Build state graph based on workflow plan
        graph = self._build_graph(workflow_plan)

        # Execute the workflow
        try:
            final_state = graph.invoke(initial_state)

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

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                node_results={},
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

        def node_node(state: GraphState) -> GraphState:
            """Execute the node and update state."""
            node = self._get_node(node_name)

            # Prepare context for node
            context = {
                "vault_summary": state["vault_summary"],
                "strategy": state["strategy"],
                "prompts": state["prompts"],
                "backend": state["backend"],
                "accumulated_changes": state["accumulated_changes"],
                "node_results": state["node_results"],
            }

            # Add metadata from previous nodes to context
            for _prev_node_name, prev_result in state["node_results"].items():
                if "metadata" in prev_result:
                    context.update(prev_result["metadata"])

            # Execute node (nodes no longer receive vault_path, they use VaultService)
            result: NodeResult = node.execute(context)

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
