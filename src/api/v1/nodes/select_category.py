"""Node responsible for selecting a category to analyze."""

from pathlib import Path
from typing import Dict, List, Optional

from src.container import DependencyContainer
from src.protocols import NodeProtocol
from src.state import AgentResult


class SelectCategoryNode(NodeProtocol):
    """Choose the category that will be used for downstream analysis."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def get_name(self) -> str:
        return "select_category"

    def validate_input(self, context: Dict) -> bool:
        requested_category = context.get("requested_category")
        return requested_category is None or isinstance(requested_category, str)

    def execute(self, vault_path: Path, context: Dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError("requested_category must be a string when provided")

        vault_service = self._container.get_vault_service()
        categories: List[str] = vault_service.get_all_categories(vault_path)

        if not categories:
            return AgentResult(
                success=False,
                changes=[],
                message="No categories were found in the vault.",
                metadata={"state_updates": {"available_categories": []}},
            )

        requested_category: Optional[str] = context.get("requested_category")
        if requested_category and requested_category in categories:
            selected_category = requested_category
        else:
            selected_category = categories[0]

        metadata = {
            "state_updates": {
                "available_categories": categories,
                "selected_category": selected_category,
            }
        }

        message = (
            f"Selected category '{selected_category}' from {len(categories)} available categories."
        )

        return AgentResult(success=True, changes=[], message=message, metadata=metadata)
