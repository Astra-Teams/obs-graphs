from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.v1.nodes.extract_keywords import ExtractKeywordsNode


def _build_container(category_content: str, llm_response: str):
    container = MagicMock()
    vault_service = MagicMock()
    vault_service.get_concatenated_content_from_category.return_value = category_content
    container.get_vault_service.return_value = vault_service
    llm = MagicMock()
    llm.generate.return_value = llm_response
    container.get_ollama_client.return_value = llm
    return container, vault_service, llm


def test_extract_keywords_happy_path():
    container, vault_service, llm = _build_container(
        "# Async IO\nPython async patterns explained", '{"keywords": ["async", "concurrency"]}'
    )
    node = ExtractKeywordsNode(container)

    result = node.execute(Path("/tmp"), {"selected_category": "Programming"})

    assert result.success is True
    updates = result.metadata["state_updates"]
    assert updates["keywords"] == ["async", "concurrency"]
    assert "Async IO" in updates["existing_titles"][0]
    vault_service.get_concatenated_content_from_category.assert_called_once()
    llm.generate.assert_called_once()


def test_extract_keywords_handles_empty_content():
    container, vault_service, llm = _build_container("   ", "{}")
    node = ExtractKeywordsNode(container)

    result = node.execute(Path("/tmp"), {"selected_category": "Programming"})

    assert result.success is False
    assert result.metadata["state_updates"]["keywords"] == []
    llm.generate.assert_not_called()


def test_extract_keywords_invalid_context_raises():
    container, *_ = _build_container("content", "{}")
    node = ExtractKeywordsNode(container)

    with pytest.raises(ValueError):
        node.execute(Path("/tmp"), {})
