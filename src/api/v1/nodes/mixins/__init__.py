"""Mixins for agent implementations (similar to Swift's Protocol extensions)."""

from .agent_defaults_mixin import AgentDefaultsMixin
from .vault_scan_mixin import VaultScanMixin

__all__ = ["AgentDefaultsMixin", "VaultScanMixin"]
