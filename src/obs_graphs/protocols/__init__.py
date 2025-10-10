"""Protocol definitions for core interfaces."""

from .github_client_protocol import GithubClientProtocol
from .nodes_protocol import NodeProtocol
from .research_client_protocol import ResearchClientProtocol, ResearchResult
from .vault_protocol import VaultServiceProtocol

__all__ = [
    "GithubClientProtocol",
    "VaultServiceProtocol",
    "NodeProtocol",
    "ResearchClientProtocol",
    "ResearchResult",
]
