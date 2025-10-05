"""Client modules for Obsidian Vault workflow automation."""

from .github_client import GithubClient
from .ollama_client import OllamaClient

__all__ = ["GithubClient", "OllamaClient"]
