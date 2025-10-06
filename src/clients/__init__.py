"""Client modules for Obsidian Vault workflow automation."""

from .github_client import GithubClient
from .research_api_client import ResearchApiClient

__all__ = ["GithubClient", "ResearchApiClient"]
