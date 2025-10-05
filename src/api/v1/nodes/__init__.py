"""Node modules for Obsidian Vault workflow automation."""

from src.state import AgentResult, FileChange

from .base import BaseAgent

__all__ = ["BaseAgent", "AgentResult", "FileChange"]
