"""Protocol definitions for core interfaces."""

from .github_client_protocol import GithubClientProtocol
from .nodes_protocol import NodeProtocol
from .vault_protocol import VaultServiceProtocol

__all__ = ["GithubClientProtocol", "VaultServiceProtocol", "NodeProtocol"]
