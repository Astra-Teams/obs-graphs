"""Client for GitHub API operations."""

from typing import Optional

from github import Github, GithubException
from github.GitTree import GitTree
from github.PullRequest import PullRequest

from src.protocols import GithubClientProtocol
from src.settings import ObsGraphsSettings


class GithubClient(GithubClientProtocol):
    """
    Client for GitHub API operations.

    This client handles GitHub Personal Access Token authentication and provides
    methods for repository operations via the GitHub API.
    """

    def __init__(self, settings: ObsGraphsSettings):
        """Initialize the GitHub client with settings."""
        self.settings = settings
        self._github_client: Optional[Github] = None

    def authenticate(self) -> Github:
        """
        Authenticate using Personal Access Token.

        Returns:
            Authenticated GitHub API client.

        Raises:
            ValueError: If GitHub PAT is not configured.
        """
        if self._github_client is not None:
            return self._github_client

        # Validate required settings
        if not self.settings.VAULT_GITHUB_TOKEN:
            raise ValueError(
                "GitHub Personal Access Token not configured. Set VAULT_GITHUB_TOKEN."
            )

        # Create authenticated client with PAT
        self._github_client = Github(
            self.settings.VAULT_GITHUB_TOKEN,
            timeout=self.settings.GITHUB_API_TIMEOUT_SECONDS,
        )
        return self._github_client

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """
        Create new branch from base branch via GitHub API.

        Args:
            branch_name: Name of the new branch to create.
            base_branch: Base branch to create from (default: "main").

        Raises:
            Exception: If branch creation fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(self.settings.OBSIDIAN_VAULT_REPO_FULL_NAME)

            # Get the base branch reference
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            base_sha = base_ref.object.sha

            # Create new branch reference
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

        except GithubException as e:
            raise Exception(f"Failed to create branch '{branch_name}': {e}")

    def get_file_content(self, path: str, branch: str) -> str:
        """
        Get file content from repository via GitHub API.

        Args:
            path: Path to the file in the repository.
            branch: Branch name to get the file from.

        Returns:
            File content as string.

        Raises:
            Exception: If file retrieval fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(self.settings.OBSIDIAN_VAULT_REPO_FULL_NAME)

            # Get file content from specified branch
            file_content = repo.get_contents(path, ref=branch)

            # Decode content (GitHub API returns base64 encoded content)
            return file_content.decoded_content.decode("utf-8")

        except GithubException as e:
            raise Exception(f"Failed to get file content for '{path}': {e}")

    def create_pull_request(
        self, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        """
        Create pull request via GitHub API.

        Args:
            head: Name of the branch containing changes.
            base: Base branch to merge into.
            title: Title of the pull request.
            body: Description/body of the pull request.

        Returns:
            PullRequest object with URL and other details.

        Raises:
            Exception: If PR creation fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(self.settings.OBSIDIAN_VAULT_REPO_FULL_NAME)

            # Create pull request
            pr = repo.create_pull(title=title, body=body, head=head, base=base)

            return pr

        except GithubException as e:
            raise Exception(f"Failed to create pull request: {e}")

    def get_tree(self, branch: str, recursive: bool = False) -> GitTree:
        """
        Get repository tree (file list) via GitHub API.

        Args:
            branch: Branch name to get the tree from.
            recursive: Whether to get the tree recursively (default: False).

        Returns:
            GitTree object containing file information.

        Raises:
            Exception: If tree retrieval fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(self.settings.OBSIDIAN_VAULT_REPO_FULL_NAME)

            # Get branch reference to get the tree SHA
            branch_ref = repo.get_git_ref(f"heads/{branch}")
            commit = repo.get_git_commit(branch_ref.object.sha)

            # Get tree
            tree = repo.get_git_tree(commit.tree.sha, recursive=recursive)

            return tree

        except GithubException as e:
            raise Exception(f"Failed to get tree for branch '{branch}': {e}")

    def bulk_commit_changes(self, branch: str, changes: list, message: str) -> str:
        """
        Commit multiple file changes atomically using Git Trees API.

        This is the most efficient way to make multiple changes, requiring only
        3-4 API calls regardless of the number of files changed.

        Args:
            branch: Branch name to commit to.
            changes: List of dicts with 'path', 'content' (or None for delete), 'action'.
            message: Commit message.

        Returns:
            SHA of the created commit.

        Raises:
            Exception: If bulk commit fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(self.settings.OBSIDIAN_VAULT_REPO_FULL_NAME)

            # 1. Get the latest commit SHA of the branch
            branch_ref = repo.get_git_ref(f"heads/{branch}")
            base_commit_sha = branch_ref.object.sha
            base_commit = repo.get_git_commit(base_commit_sha)
            base_tree_sha = base_commit.tree.sha

            # If no changes, return the base commit SHA without creating a new commit
            if not changes:
                return base_commit_sha

            # 2. Prepare tree elements for the new tree
            tree_elements = []
            for change in changes:
                path = change["path"]
                action = change["action"]
                content = change.get("content")

                if action == "delete":
                    # For deletion, we simply omit the file from the new tree
                    # PyGithub doesn't support explicit deletion in tree creation,
                    # so we need to get the base tree and exclude the deleted file
                    continue
                else:
                    # For create/update, create a blob and add to tree
                    if content is not None:
                        # Create blob for file content
                        blob = repo.create_git_blob(content, "utf-8")
                        tree_elements.append(
                            {
                                "path": path,
                                "mode": "100644",  # Regular file
                                "type": "blob",
                                "sha": blob.sha,
                            }
                        )

            # Get base tree to preserve existing files not in changes
            base_tree = repo.get_git_tree(base_tree_sha, recursive=True)
            changed_paths = {change["path"] for change in changes}
            for element in base_tree.tree:
                if element.path not in changed_paths and element.type == "blob":
                    # Include files that aren't being changed
                    tree_elements.append(
                        {
                            "path": element.path,
                            "mode": element.mode,
                            "type": element.type,
                            "sha": element.sha,
                        }
                    )

            # 3. Create new tree
            new_tree = repo.create_git_tree(tree_elements)

            # 4. Create new commit
            new_commit = repo.create_git_commit(
                message=message,
                tree=new_tree,
                parents=[base_commit],
            )

            # 5. Update branch reference
            branch_ref.edit(sha=new_commit.sha, force=False)

            return new_commit.sha

        except GithubException as e:
            raise Exception(f"Failed to bulk commit changes: {e}")
