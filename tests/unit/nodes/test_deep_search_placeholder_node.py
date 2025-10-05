from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.deep_search_placeholder import DeepSearchPlaceholderNode


def test_deep_search_placeholder_generates_report():
    container = MagicMock()
    node = DeepSearchPlaceholderNode(container)

    result = node.execute(Path("/tmp"), {"selected_theme": "Test Theme"})

    assert result.success is True
    report = result.metadata["state_updates"]["report_markdown"]
    assert "Test Theme" in report
    assert "deep-search" in report


def test_deep_search_placeholder_requires_theme():
    container = MagicMock()
    node = DeepSearchPlaceholderNode(container)

    with pytest.raises(ValueError):
        node.execute(Path("/tmp"), {})
