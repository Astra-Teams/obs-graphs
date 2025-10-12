"""Protocol definitions for core interfaces."""

from .github_client_protocol import GithubClientProtocol
from .github_service_protocol import GithubServiceProtocol
from .llm_client_protocol import LLMClientProtocol
from .nodes_protocol import NodeProtocol
from .research_client_protocol import ResearchClientProtocol, ResearchResult
from .vault_protocol import VaultServiceProtocol

__all__ = [
    "GithubClientProtocol",
    "VaultServiceProtocol",
    "GithubServiceProtocol",
    "NodeProtocol",
    "LLMClientProtocol",
    "ResearchClientProtocol",
    "ResearchResult",
]
