"""Client modules for Obsidian Vault workflow automation."""

from .mlx_client import MLXClient
from .ollama_client import OllamaClient

__all__ = [
    "OllamaClient",
    "MLXClient",
]
