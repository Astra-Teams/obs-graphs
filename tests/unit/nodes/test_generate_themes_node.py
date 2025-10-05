from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.generate_themes import GenerateThemesNode


def _build_container(llm_response: str):
    container = MagicMock()
    llm = MagicMock()
    llm.generate.return_value = llm_response
    container.get_ollama_client.return_value = llm
    return container, llm


def test_generate_themes_success():
    container, llm = _build_container('{"themes": ["Theme A", "Theme B"]}')
    node = GenerateThemesNode(container)

    result = node.execute(
        Path("/tmp"),
        {"keywords": ["async"], "existing_titles": ["Old Theme"]},
    )

    assert result.success is True
    updates = result.metadata["state_updates"]
    assert updates["themes"] == ["Theme A", "Theme B"]
    assert updates["selected_theme"] == "Theme A"
    llm.generate.assert_called_once()


def test_generate_themes_failure_on_invalid_json():
    container, llm = _build_container("unexpected")
    node = GenerateThemesNode(container)

    result = node.execute(Path("/tmp"), {"keywords": ["async"]})

    assert result.success is False
    assert result.metadata["state_updates"]["themes"] == []
    llm.generate.assert_called_once()


def test_generate_themes_requires_keywords():
    container, _ = _build_container("{}")
    node = GenerateThemesNode(container)

    with pytest.raises(ValueError):
        node.execute(Path("/tmp"), {"keywords": []})
