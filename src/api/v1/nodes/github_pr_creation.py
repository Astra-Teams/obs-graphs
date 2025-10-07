"""Agent for creating GitHub pull requests from workflow results."""

from src.protocols import GithubClientProtocol, NodeProtocol
from src.settings import get_settings
from src.state import AgentResult, FileChange


class GithubPRCreationAgent(NodeProtocol):
    """
    Agent responsible for creating GitHub pull requests.

    This agent only handles PR creation. Committing changes is handled by
    CommitChangesAgent, which should run before this agent.
    """

    def __init__(self, github_client: GithubClientProtocol):
        """Initialize the GitHub PR creation agent."""
        self.github_client = github_client
        self._settings = get_settings()

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information.

        Args:
            context: Must contain 'strategy', 'accumulated_changes', 'node_results', and 'branch_name'

        Returns:
            True if context is valid, False otherwise
        """
        required_keys = [
            "strategy",
            "accumulated_changes",
            "node_results",
            "branch_name",
        ]
        return all(key in context for key in required_keys)

    def execute(self, context: dict) -> AgentResult:
        """
        Execute GitHub PR creation workflow.

        Args:
            context: Dictionary containing strategy, accumulated_changes, node_results, and branch_name

        Returns:
            AgentResult with PR URL in metadata

        Raises:
            ValueError: If input validation fails
        """
        if not self.validate_input(context):
            raise ValueError(
                "Invalid context: strategy, accumulated_changes, node_results, and branch_name are required"
            )

        strategy = context["strategy"]
        accumulated_changes: list[FileChange] = context["accumulated_changes"]
        node_results: dict = context["node_results"]
        branch_name: str = context["branch_name"]

        try:
            # If no changes were committed, don't create PR
            commit_result = node_results.get("commit_changes", {})
            if not commit_result.get("success") or not accumulated_changes:
                return AgentResult(
                    success=True,
                    changes=[],
                    message="No changes committed, skipping PR creation",
                    metadata={"branch_name": branch_name, "pr_url": ""},
                )

            # Create pull request
            pr_title, pr_body = self._generate_pr_content(
                strategy, node_results, accumulated_changes
            )

            pr = self.github_client.create_pull_request(
                head=branch_name,
                base=self._settings.WORKFLOW_DEFAULT_BRANCH,
                title=pr_title,
                body=pr_body,
            )

            return AgentResult(
                success=True,
                changes=[],
                message=f"Pull request created successfully: {pr.html_url}",
                metadata={"branch_name": branch_name, "pr_url": pr.html_url},
            )

        except Exception as e:
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to create pull request: {str(e)}",
                metadata={"error": str(e)},
            )

    def _generate_pr_content(
        self, strategy: str, node_results: dict, changes: list[FileChange]
    ) -> tuple[str, str]:
        """
        Generate pull request title and body.

        Args:
            strategy: Workflow strategy name
            node_results: Results from executed nodes
            changes: List of file changes

        Returns:
            Tuple of (title, body)
        """
        # Customize title for research proposals
        if strategy == "research_proposal":
            # Extract proposal title from deep_research metadata
            deep_research_result = node_results.get("deep_research", {})
            proposal_metadata = deep_research_result.get("metadata", {})
            proposal_filename = proposal_metadata.get(
                "proposal_filename", "research proposal"
            )
            title = f"Research Proposal: {proposal_filename.replace('.md', '').replace('-', ' ').title()}"
        else:
            title = f"Automated vault improvements ({strategy})"

        # Filter out meta-nodes from results to be displayed in the PR body
        user_facing_node_results = {
            name: res
            for name, res in node_results.items()
            if name not in ["commit_changes", "github_pr_creation"]
        }

        # Generate summary
        summary_parts = []
        for node_name, result in user_facing_node_results.items():
            if result["success"]:
                summary_parts.append(f"- {node_name}: {result['message']}")
        summary = "\n".join(summary_parts)

        # Build PR body with strategy-specific content
        if strategy == "research_proposal":
            body_parts = [
                "## Research Proposal",
                "\n### Overview",
                "This PR contains a new research proposal generated from a user prompt.",
            ]

            # Add proposal metadata if available
            article_proposal_result = node_results.get("article_proposal", {})
            article_metadata = article_proposal_result.get("metadata", {})

            if "topic_title" in article_metadata:
                body_parts.append(f"\n**Topic**: {article_metadata['topic_title']}")
            if "tags" in article_metadata:
                tags_str = ", ".join(article_metadata["tags"])
                body_parts.append(f"**Tags**: {tags_str}")

            deep_research_result = node_results.get("deep_research", {})
            deep_metadata = deep_research_result.get("metadata", {})
            if "sources_count" in deep_metadata:
                body_parts.append(
                    f"**Sources**: {deep_metadata['sources_count']} references"
                )

            body_parts.extend(
                [
                    "\n### Summary",
                    summary,
                    "\n### Details",
                    f"- **Proposal File**: {deep_metadata.get('proposal_path', 'N/A')}",
                    f"- **Total Changes**: {len(changes)} file operation(s)",
                    f"- **Nodes Executed**: {len(user_facing_node_results)}",
                ]
            )
        else:
            body_parts = [
                "## Automated Vault Improvements",
                f"\n**Strategy**: {strategy}",
                "\n### Summary",
                summary,
                "\n### Details",
                f"- **Total Changes**: {len(changes)} file operations",
                f"- **Nodes Executed**: {len(user_facing_node_results)}",
            ]

        # Add commit info if available
        commit_result = node_results.get("commit_changes", {})
        if commit_result.get("metadata", {}).get("commit_sha"):
            commit_sha = commit_result["metadata"]["commit_sha"]
            body_parts.append(f"- **Commit**: `{commit_sha[:7]}`")

        body_parts.append("\n### Node Results")

        for node_name, result in user_facing_node_results.items():
                body_parts.append(f"\n#### {node_name}")
                body_parts.append(
                    f"- Status: {'✅ Success' if result['success'] else '❌ Failed'}"
                )
                body_parts.append(f"- Message: {result['message']}")
                body_parts.append(f"- Changes: {result['changes_count']}")

        body_parts.append("\n---\n*Generated by Obsidian Nodes Workflow Automation*")

        body = "\n".join(body_parts)

        return title, body
