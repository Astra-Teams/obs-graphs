"""Placeholder node for deep-search API integration."""

from pathlib import Path
from typing import Dict

from src.container import DependencyContainer
from src.protocols import NodeProtocol
from src.state import AgentResult


class DeepSearchPlaceholderNode(NodeProtocol):
    """Generate a stub markdown report for a selected theme."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def get_name(self) -> str:
        return "deep_search_placeholder"

    def validate_input(self, context: Dict) -> bool:
        return isinstance(context.get("selected_theme"), str)

    def execute(self, vault_path: Path, context: Dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError("selected_theme must be provided before deep search placeholder")

        theme = context["selected_theme"]
        report = f"## {theme}についてのレポート\n\n（ここにdeep-searchの結果が入ります）"

        metadata = {"state_updates": {"report_markdown": report}}
        message = f"Generated placeholder report for theme '{theme}'."
        return AgentResult(success=True, changes=[], message=message, metadata=metadata)
