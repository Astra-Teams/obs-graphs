"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

from src.api.v1.schemas import WorkflowRunRequest
from src.container import DependencyContainer
from src.settings import get_settings
from src.state import AgentResult, FileChange, GraphState


@dataclass
class WorkflowPlan:
    """
    Plan for workflow execution.

    Attributes:
        nodes: Ordered list of node names to execute
        strategy: Workflow strategy (new_article or improvement)
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
        pr_url: URL of the created pull request
        branch_name: Name of the created branch
    """

    success: bool
    changes: list[FileChange]
    summary: str
    node_results: dict = field(default_factory=dict)
    pr_url: str = ""
    branch_name: str = ""


class GraphBuilder:
    """
    Builds and orchestrates the execution of nodes using LangGraph.

    This class analyzes the vault to determine which nodes should run,
    then executes them in the appropriate order using a state graph.
    """

    def run_workflow(self, request: WorkflowRunRequest) -> WorkflowResult:
        """
        Run the complete workflow via GitHub API: create branch, execute nodes, create PR.

        Args:
            request: Workflow run request with optional strategy override

        Returns:
            WorkflowResult with execution results
        """
        settings = get_settings()

        try:
            # Instantiate DependencyContainer
            container = DependencyContainer()

            # Get required services and clients
            github_client = container.get_github_client()

            # Create new branch for this workflow
            branch_name = f"obsidian-agents/workflow-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            github_client.create_branch(
                branch_name=branch_name,
                base_branch=settings.workflow_default_branch,
            )

            # Set the branch in the container for workflow execution
            container.set_branch(branch_name)

            # Analyze vault to create workflow plan
            vault_service = container.get_vault_service()
            workflow_plan = self.determine_workflow_plan(vault_service, request)

            # Override strategy if specified in request
            if request.strategy:
                workflow_plan.strategy = request.strategy

            # Execute workflow
            workflow_result = self.execute_workflow(
                branch_name, workflow_plan, container, request.prompt
            )

            if not workflow_result.success:
                raise Exception(f"Workflow execution failed: {workflow_result.summary}")

            # Update result with PR info from github_pr_creation node
            pr_result = workflow_result.node_results.get("github_pr_creation", {})
            pr_metadata = pr_result.get("metadata", {})
            workflow_result.pr_url = pr_metadata.get("pr_url", "")
            workflow_result.branch_name = branch_name

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

        If a prompt is provided, uses research_proposal strategy.
        Otherwise, uses new_article strategy.

        Args:
            vault_service: Vault service instance
            request: Workflow run request

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        # Check if this is a research workflow (prompt provided)
        if request.prompt and request.prompt.strip():
            strategy = "research_proposal"
            nodes = [
                "article_proposal",
                "deep_research",
                "commit_changes",
                "github_pr_creation",
            ]
        else:
            # Default: new article creation strategy
            strategy = "new_article"
            nodes = [
                "article_proposal",
                "article_content_generation",
                "commit_changes",
                "github_pr_creation",
            ]

        return WorkflowPlan(nodes=nodes, strategy=strategy)

    def execute_workflow(
        self,
        branch_name: str,
        workflow_plan: WorkflowPlan,
        container: DependencyContainer,
        prompt: str = "",
    ) -> WorkflowResult:
        """
        Execute workflow using LangGraph state graph.

        Args:
            branch_name: Branch name for this workflow
            workflow_plan: Plan specifying which nodes to run
            container: Dependency container
            prompt: User prompt for research workflows

        Returns:
            WorkflowResult with aggregated changes and results
        """
        # Initialize workflow state
        initial_state: GraphState = {
            "branch_name": branch_name,
            "vault_summary": {},  # Nodes can fetch what they need via VaultService
            "strategy": workflow_plan.strategy,
            "prompt": prompt,
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
                "previous_changes": state["accumulated_changes"],
                "previous_results": state["node_results"],
                "branch_name": state["branch_name"],
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
