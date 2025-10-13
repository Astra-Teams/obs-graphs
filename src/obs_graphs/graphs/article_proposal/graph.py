"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

from dataclasses import dataclass, field

from langgraph.graph import END, StateGraph

from src.obs_graphs.api.schemas import WorkflowRunRequest
from src.obs_graphs.config import obs_graphs_settings
from src.obs_graphs.container import DependencyContainer, get_container
from src.obs_graphs.graphs.article_proposal.state import (
    AgentResult,
    FileChange,
    GraphState,
    WorkflowStrategy,
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

    def run_workflow(self, request: WorkflowRunRequest) -> WorkflowResult:
        """
        Run the complete workflow: execute nodes and submit the draft via obs-gtwy.

        Args:
            request: Workflow run request with optional strategy override

        Returns:
            WorkflowResult with execution results
        """

        try:
            # Instantiate DependencyContainer
            container = get_container()

            # Analyze vault to create workflow plan
            vault_service = container.get_vault_service()
            workflow_plan = self.determine_workflow_plan(vault_service, request)

            # Override strategy if specified in request
            if request.strategy:
                workflow_plan.strategy = request.strategy

            # Execute workflow
            workflow_result = self.execute_workflow(
                workflow_plan,
                container,
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
        vault_service,
        request: WorkflowRunRequest,
    ) -> WorkflowPlan:
        """
        Analyze vault and request to determine which nodes to run and in what order.

        The workflow now requires a prompt and always uses the research_proposal strategy.

        Args:
            vault_service: Vault service instance
            request: Workflow run request

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        if not request.prompts:
            raise ValueError("At least one prompt is required to run the workflow")

        primary_prompt = request.primary_prompt
        if not primary_prompt:
            raise ValueError("The first prompt cannot be empty")

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
        container: DependencyContainer,
        prompts: list[str] | None = None,
        backend: str | None = None,
    ) -> WorkflowResult:
        """
        Execute workflow using LangGraph state graph.

        Args:
            workflow_plan: Plan specifying which nodes to run
            container: Dependency container
            prompts: User prompts for research workflows (list of strings)

        Returns:
            WorkflowResult with aggregated changes and results
        """
        # Initialize workflow state
        vault_service = container.get_vault_service()
        vault_summary = vault_service.get_vault_summary()

        selected_backend = (backend or obs_graphs_settings.llm_backend).strip().lower()

        prompt_list = prompts or []

        initial_state: GraphState = {
            "vault_summary": vault_summary,
            "strategy": workflow_plan.strategy,
            "prompt": prompt_list,
            "backend": selected_backend,
            "accumulated_changes": [],
            "node_results": {},
            "messages": [],
        }

        # Build state graph based on workflow plan
        graph = self._build_graph(workflow_plan, container)

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

    def _build_graph(
        self, workflow_plan: WorkflowPlan, container: DependencyContainer
    ) -> StateGraph:
        """
        Build LangGraph state graph based on workflow plan.

        Args:
            workflow_plan: Plan specifying node execution order
            container: Dependency container

        Returns:
            Configured StateGraph ready for execution
        """
        # Create state graph
        workflow = StateGraph(GraphState)

        # Add node nodes
        for node_name in workflow_plan.nodes:
            workflow.add_node(node_name, self._create_node_node(node_name, container))

        # Add edges to create sequential execution
        workflow.set_entry_point(workflow_plan.nodes[0])

        for i in range(len(workflow_plan.nodes) - 1):
            current_node = workflow_plan.nodes[i]
            next_node = workflow_plan.nodes[i + 1]
            workflow.add_edge(current_node, next_node)

        # Last node leads to END
        workflow.add_edge(workflow_plan.nodes[-1], END)

        return workflow.compile()

    def _create_node_node(self, node_name: str, container: DependencyContainer):
        """
        Create a node function for the specified node.

        Args:
            node_name: Name of the node to create node for
            container: Dependency container

        Returns:
            Callable node function for use in state graph
        """

        def node_node(state: GraphState) -> GraphState:
            """Execute the node and update state."""
            node = container.get_node(node_name)

            # Prepare context for node
            context = {
                "vault_summary": state["vault_summary"],
                "strategy": state["strategy"],
                "prompt": state["prompt"],
                "backend": state["backend"],
                "accumulated_changes": state["accumulated_changes"],
                "node_results": state["node_results"],
            }

            # Add metadata from previous nodes to context
            for _prev_node_name, prev_result in state["node_results"].items():
                if "metadata" in prev_result:
                    context.update(prev_result["metadata"])

            # Execute node (nodes no longer receive vault_path, they use VaultService)
            result: AgentResult = node.execute(context)

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
