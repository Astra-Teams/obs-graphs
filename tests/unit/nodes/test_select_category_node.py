from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.select_category import SelectCategoryNode


class _Container:
    def __init__(self, categories):
        self.vault_service = MagicMock()
        self.vault_service.get_all_categories.return_value = categories

    def get_vault_service(self):
        return self.vault_service


def test_select_category_prefers_requested_category():
    container = _Container(["Programming", "AI"])
    node = SelectCategoryNode(container)

    result = node.execute(Path("/tmp"), {"requested_category": "AI"})

    assert result.success is True
    assert result.metadata["state_updates"]["selected_category"] == "AI"
    container.vault_service.get_all_categories.assert_called_once()


def test_select_category_defaults_to_first_category():
    container = _Container(["Programming", "AI"])
    node = SelectCategoryNode(container)

    result = node.execute(Path("/tmp"), {"requested_category": "Unknown"})

    assert result.metadata["state_updates"]["selected_category"] == "Programming"


def test_select_category_returns_failure_when_empty():
    container = _Container([])
    node = SelectCategoryNode(container)

    result = node.execute(Path("/tmp"), {})

    assert result.success is False
    assert result.metadata["state_updates"]["available_categories"] == []


def test_select_category_invalid_input_raises():
    container = _Container(["Programming"])
    node = SelectCategoryNode(container)

    with pytest.raises(ValueError):
        node.execute(Path("/tmp"), {"requested_category": 123})
