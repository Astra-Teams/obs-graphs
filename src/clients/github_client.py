"""Client for GitHub Personal Access Token authentication and repository operations."""

from pathlib import Path
from typing import Optional

from git import Repo
from github import Github, GithubException
from github.PullRequest import PullRequest

from src.protocols import GithubClientProtocol
from src.settings import ObsGraphsSettings


class GithubClient(GithubClientProtocol):
    """
    Client for GitHub operations including authentication, cloning, and PR creation.

    This client handles GitHub Personal Access Token authentication and provides
    methods for repository operations needed in the workflow automation system.
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
        if not self.settings.GITHUB_PAT:
            raise ValueError(
                "GitHub Personal Access Token not configured. Set GITHUB_PAT."
            )

        # Create authenticated client with PAT
        self._github_client = Github(self.settings.GITHUB_PAT)
        return self._github_client

    def clone_repository(self, target_path: Path, branch: str = "main") -> None:
        """
        Clone repository to local path using git commands with authentication.

        Args:
            target_path: Local directory path where repository will be cloned.
            branch: Branch name to checkout (default: "main").

        Raises:
            Exception: If cloning fails.
        """
        try:
            # Ensure target directory doesn't exist
            if target_path.exists():
                raise FileExistsError(f"Target path already exists: {target_path}")

            # Create parent directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Get authenticated clone URL
            repo_url = self.get_authenticated_clone_url(
                self.settings.GITHUB_REPO_FULL_NAME
            )

            # Clone the repository
            repo = Repo.clone_from(
                repo_url,
                target_path,
                branch=branch,
                depth=1,  # Shallow clone for efficiency
            )

            # Ensure we're on the correct branch
            if repo.active_branch.name != branch:
                repo.git.checkout(branch)

        except Exception as e:
            raise Exception(f"Failed to clone repository: {e}")

    def create_branch(self, repo_path: Path, branch_name: str) -> None:
        """
        Create new git branch from the current branch.

        Args:
            repo_path: Path to the local git repository.
            branch_name: Name of the new branch to create.

        Raises:
            FileNotFoundError: If repository path doesn't exist.
            Exception: If branch creation fails.
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")

        try:
            repo = Repo(repo_path)

            # Ensure we're on the default branch before creating new branch
            default_branch = self.settings.WORKFLOW_DEFAULT_BRANCH
            if repo.active_branch.name != default_branch:
                repo.git.checkout(default_branch)

            # Create and checkout new branch
            repo.git.checkout("-b", branch_name)

        except Exception as e:
            raise Exception(f"Failed to create branch '{branch_name}': {e}")

    def commit_and_push(self, repo_path: Path, branch_name: str, message: str) -> bool:
        """
        Stage all changes, commit, and push to remote branch.

        Args:
            repo_path: Path to the local git repository.
            branch_name: Name of the branch to push.
            message: Commit message.

        Returns:
            True if changes were committed and pushed, False if there were no changes.

        Raises:
            FileNotFoundError: If repository path doesn't exist.
            Exception: If commit or push fails.
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")

        try:
            repo = Repo(repo_path)

            # Stage all changes (including untracked files)
            repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                return False

            # Commit changes
            repo.index.commit(message)

            # Push to remote
            origin = repo.remote(name="origin")
            origin.push(refspec=f"{branch_name}:{branch_name}")

            return True

        except Exception as e:
            raise Exception(f"Failed to commit and push to branch '{branch_name}': {e}")

    def create_pull_request(
        self,
        repo_full_name: str,
        head_branch: str,
        title: str,
        body: str,
        base_branch: Optional[str] = None,
    ) -> PullRequest:
        """
        Create pull request via GitHub API.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo").
            head_branch: Name of the branch containing changes.
            title: Title of the pull request.
            body: Description/body of the pull request.
            base_branch: Base branch to merge into (default: from settings).

        Returns:
            PullRequest object with URL and other details.

        Raises:
            Exception: If PR creation fails.
        """
        try:
            github_client = self.authenticate()
            repo = github_client.get_repo(repo_full_name)

            # Use default branch if base_branch not specified
            if base_branch is None:
                base_branch = self.settings.WORKFLOW_DEFAULT_BRANCH

            # Create pull request
            pr = repo.create_pull(
                title=title, body=body, head=head_branch, base=base_branch
            )

            return pr

        except GithubException as e:
            raise Exception(f"Failed to create pull request: {e}")

    def get_authenticated_clone_url(self, repo_full_name: str) -> str:
        """
        Get authenticated clone URL for the repository.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo").

        Returns:
            HTTPS clone URL with authentication token embedded.
        """
        # Construct authenticated URL with PAT
        return f"https://x-access-token:{self.settings.GITHUB_PAT}@github.com/{repo_full_name}.git"
