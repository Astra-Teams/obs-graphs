"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from langgraph.graph import END, StateGraph

from src.api.v1.schemas import WorkflowRunRequest
from src.container import DependencyContainer
from src.protocols import VaultServiceProtocol
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
        Run the complete workflow: clone repo, analyze vault, execute nodes, commit changes, create PR.

        Args:
            request: Workflow run request with optional strategy override

        Returns:
            WorkflowResult with execution results
        """
        settings = get_settings()
        temp_path = None

        try:
            # Instantiate DependencyContainer
            container = DependencyContainer()

            # Get required services and clients
            github_client = container.get_github_client()
            vault_service = container.get_vault_service()

            # Create temporary directory for vault clone
            clone_base_path = Path(settings.WORKFLOW_CLONE_BASE_PATH)
            clone_base_path.mkdir(parents=True, exist_ok=True)
            temp_path = (
                clone_base_path / f"workflow_{datetime.now(timezone.utc).timestamp()}"
            )

            # Clone repository
            github_client.clone_repository(
                target_path=temp_path,
                branch=settings.WORKFLOW_DEFAULT_BRANCH,
            )

            # Analyze vault to create workflow plan
            workflow_plan = self.analyze_vault(temp_path, vault_service)

            # Override strategy if specified in request
            if request.strategy:
                workflow_plan.strategy = request.strategy

            # Execute workflow
            workflow_result = self.execute_workflow(temp_path, workflow_plan, container)

            if not workflow_result.success:
                raise Exception(f"Workflow execution failed: {workflow_result.summary}")

            # Apply changes to vault
            vault_service.apply_changes(temp_path, workflow_result.changes)

            # Validate vault structure after changes
            if not vault_service.validate_vault_structure(temp_path):
                raise Exception(
                    "Vault structure validation failed after applying changes"
                )

            # Update result with PR info from github_pr_creation node
            pr_result = workflow_result.node_results.get("github_pr_creation", {})
            pr_metadata = pr_result.get("metadata", {})
            workflow_result.pr_url = pr_metadata.get("pr_url", "")
            workflow_result.branch_name = pr_metadata.get("branch_name", "")

            return workflow_result

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                node_results={},
            )

        finally:
            # Clean up temporary directory
            if temp_path and temp_path.exists():
                try:
                    shutil.rmtree(temp_path)
                except Exception:
                    # Log cleanup error but don't fail
                    pass

    def analyze_vault(
        self, vault_path: Path, vault_service: VaultServiceProtocol
    ) -> WorkflowPlan:
        """
        Analyze vault to determine which nodes to run and in what order.

        The workflow always uses the new_article strategy.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        # Always use new article creation strategy
        strategy = "new_article"
        nodes = [
            "article_proposal",
            "article_content_generation",
            "github_pr_creation",
        ]

        return WorkflowPlan(nodes=nodes, strategy=strategy)

    def execute_workflow(
        self,
        vault_path: Path,
        workflow_plan: WorkflowPlan,
        container: DependencyContainer,
    ) -> WorkflowResult:
        """
        Execute workflow using LangGraph state graph.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            workflow_plan: Plan specifying which nodes to run

        Returns:
            WorkflowResult with aggregated changes and results
        """
        # Get vault summary for context
        vault_summary = container.get_vault_service().get_vault_summary(vault_path)

        # Initialize workflow state
        initial_state: GraphState = {
            "vault_path": vault_path,
            "vault_summary": vault_summary.__dict__,  # Convert to dict for TypedDict
            "strategy": workflow_plan.strategy,
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
                "previous_changes": state["accumulated_changes"],
                "previous_results": state["node_results"],
            }

            # Execute node
            result: AgentResult = node.execute(state["vault_path"], context)

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
