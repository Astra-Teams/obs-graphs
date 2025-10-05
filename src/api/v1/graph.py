"""LangGraph-based workflow orchestration for Obsidian Vault nodes."""

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from langgraph.graph import END, StateGraph

from src.api.v1.schemas import WorkflowRunRequest
from src.container import DependencyContainer
from src.protocols.vault_protocol import VaultServiceProtocol
from src.settings import get_settings
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
        pr_url: URL of the created pull request
        branch_name: Name of the created branch
    """

    success: bool
    changes: list[FileChange]
    summary: str
    agent_results: dict = field(default_factory=dict)
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
        Run the complete workflow: clone repo, analyze vault, execute agents, commit changes, create PR.

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

            # Create new branch for changes
            branch_name = f"obsidian-agents/{workflow_plan.strategy}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            github_client.create_branch(repo_path=temp_path, branch_name=branch_name)

            # Commit and push changes
            commit_message = f"""Automated vault improvements via {workflow_plan.strategy} strategy

{workflow_result.summary}

Changes made by Obsidian Agents workflow
"""
            pushed = github_client.commit_and_push(
                repo_path=temp_path, branch_name=branch_name, message=commit_message
            )

            # If no changes were made, return success without PR
            if not pushed:
                workflow_result.pr_url = ""
                workflow_result.branch_name = branch_name
                return workflow_result

            # Create pull request
            pr_title = f"Automated vault improvements ({workflow_plan.strategy})"
            pr_body = f"""## Automated Vault Improvements

**Strategy**: {workflow_plan.strategy}

### Summary
{workflow_result.summary}

### Details
- **Total Changes**: {len(workflow_result.changes)} file operations
- **Agents Executed**: {len(workflow_result.agent_results)}

### Agent Results
"""
            for agent_name, result in workflow_result.agent_results.items():
                pr_body += f"\n#### {agent_name}\n"
                pr_body += (
                    f"- Status: {'✅ Success' if result['success'] else '❌ Failed'}\n"
                )
                pr_body += f"- Message: {result['message']}\n"
                pr_body += f"- Changes: {result['changes_count']}\n"

            pr_body += "\n---\n*Generated by Obsidian Agents Workflow Automation*"

            pr = github_client.create_pull_request(
                repo_full_name=settings.GITHUB_REPO_FULL_NAME,
                head_branch=branch_name,
                title=pr_title,
                body=pr_body,
            )

            # Update result with PR info
            workflow_result.pr_url = pr.html_url
            workflow_result.branch_name = branch_name

            return workflow_result

        except Exception as e:
            return WorkflowResult(
                success=False,
                changes=[],
                summary=f"Workflow failed: {str(e)}",
                agent_results={},
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

        Args:
            vault_path: Path to the local clone of the Obsidian Vault

        Returns:
            WorkflowPlan with ordered list of nodes and strategy
        """
        # Get vault summary for analysis
        vault_summary = vault_service.get_vault_summary(vault_path)

        total_articles = vault_summary.total_articles

        # Determine strategy based on vault state
        if total_articles < 5:
            # Empty or sparse vault - focus on new content
            strategy = "new_article"
            agents = [
                "new_article_creation",
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
            "agent_results": {},
            "messages": [],
        }

        # Build state graph based on workflow plan
        graph = self._build_graph(workflow_plan, container)

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
        for node_name in workflow_plan.agents:
            workflow.add_node(node_name, self._create_node_node(node_name, container))

        # Add edges to create sequential execution
        workflow.set_entry_point(workflow_plan.agents[0])

        for i in range(len(workflow_plan.agents) - 1):
            current_node = workflow_plan.agents[i]
            next_node = workflow_plan.agents[i + 1]
            workflow.add_edge(current_node, next_node)

        # Last node leads to END
        workflow.add_edge(workflow_plan.agents[-1], END)

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
