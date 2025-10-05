"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from langgraph.graph import END, StateGraph

from src.protocols.nodes_protocol import NodeProtocol
from src.protocols.vault_protocol import VaultServiceProtocol
from src.state import AgentResult, FileChange, GraphState


@dataclass
class WorkflowPlan:
    """
    Plan for workflow execution.

    Attributes:
        agents: Ordered list of agent names to execute
        strategy: Workflow strategy (new_article or improvement)
    """

    agents: list[str]
    strategy: str


@dataclass
class WorkflowResult:
    """
    Result of workflow execution.

    Attributes:
        success: Whether the workflow completed successfully
        changes: Aggregated list of all file changes from agents
        summary: Human-readable summary of what was done
        agent_results: Dictionary mapping agent names to their results
    """

    success: bool
    changes: list[FileChange]
    summary: str
    agent_results: dict = field(default_factory=dict)


class GraphBuilder:
    """
    Builds and orchestrates the execution of nodes using LangGraph.

    This class analyzes the vault to determine which nodes should run,
    then executes them in the appropriate order using a state graph.
    """

    def __init__(self, vault_service: VaultServiceProtocol, nodes: Dict[str, NodeProtocol]):
        """
        Initialize the graph builder with dependencies.

        Args:
            vault_service: Service for vault operations
            nodes: Dictionary of available nodes keyed by name
        """
        self.vault_service = vault_service
        self.nodes = nodes

    def analyze_vault(self, vault_path: Path) -> WorkflowPlan:
        """
        Analyze vault to determine which nodes to run and in what order.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        # Get vault summary for analysis
        vault_summary = self.vault_service.get_vault_summary(vault_path)

        total_articles = vault_summary.total_articles

        # Determine strategy based on vault state
        if total_articles < 5:
            # Empty or sparse vault - focus on new content
            strategy = "new_article"
            agents = [
                "new_article",
                "file_organization",
                "category_organization",
                "quality_audit",
                "cross_reference",
            ]
        else:
            # Existing vault - focus on improvement
            strategy = "improvement"
            agents = [
                "article_improvement",
                "file_organization",
                "category_organization",
                "quality_audit",
                "cross_reference",
            ]

        return WorkflowPlan(agents=agents, strategy=strategy)

    def execute_workflow(
        self, vault_path: Path, workflow_plan: WorkflowPlan
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
        vault_summary = self.vault_service.get_vault_summary(vault_path)

        # Initialize workflow state
        initial_state: GraphState = {
            "vault_path": vault_path,
            "vault_summary": vault_summary.__dict__,  # Convert to dict for TypedDict
            "strategy": workflow_plan.strategy,
            "accumulated_changes": [],
            "agent_results": {},
            "messages": [],
        }

        # Build state graph based on workflow plan
        graph = self._build_graph(workflow_plan)

        # Execute the workflow
        try:
            final_state = graph.invoke(initial_state)

            # Extract results from final state
            all_changes = final_state["accumulated_changes"]
            agent_results = final_state["agent_results"]

            # Generate summary
            summary = self._generate_summary(agent_results, workflow_plan.strategy)

            return WorkflowResult(
                success=True,
                changes=all_changes,
                summary=summary,
                agent_results=agent_results,
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                agent_results={},
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
        for node_name in workflow_plan.agents:
            workflow.add_node(node_name, self._create_node_node(node_name))

        # Add edges to create sequential execution
        workflow.set_entry_point(workflow_plan.agents[0])

        for i in range(len(workflow_plan.agents) - 1):
            current_node = workflow_plan.agents[i]
            next_node = workflow_plan.agents[i + 1]
            workflow.add_edge(current_node, next_node)

        # Last node leads to END
        workflow.add_edge(workflow_plan.agents[-1], END)

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
            node = self.nodes[node_name]

            # Prepare context for node
            context = {
                "vault_summary": state["vault_summary"],
                "strategy": state["strategy"],
                "previous_changes": state["accumulated_changes"],
                "previous_results": state["agent_results"],
            }

            # Execute node
            result: AgentResult = node.execute(state["vault_path"], context)

            # Update state with results
            state["accumulated_changes"].extend(result.changes)
            state["agent_results"][node_name] = {
                "success": result.success,
                "message": result.message,
                "changes_count": len(result.changes),
                "metadata": result.metadata,
            }
            state["messages"].append(
                f"{node.get_name()}: {result.message} ({len(result.changes)} changes)"
            )

            return state

        return node_node

    def _generate_summary(self, agent_results: dict, strategy: str) -> str:
        """
        Generate human-readable summary of workflow execution.

        Args:
            agent_results: Results from all executed nodes
            strategy: Workflow strategy that was used

        Returns:
            Summary string
        """
        successful_agents = [
            name for name, result in agent_results.items() if result["success"]
        ]
        total_changes = sum(
            result["changes_count"] for result in agent_results.values()
        )

        summary_parts = [
            f"Workflow completed with '{strategy}' strategy.",
            f"Executed {len(successful_agents)}/{len(agent_results)} nodes successfully.",
            f"Total changes: {total_changes} file operations.",
        ]

        # Add node-specific details
        for node_name, result in agent_results.items():
            if result["success"]:
                summary_parts.append(f"- {node_name}: {result['message']}")

        return "\n".join(summary_parts)