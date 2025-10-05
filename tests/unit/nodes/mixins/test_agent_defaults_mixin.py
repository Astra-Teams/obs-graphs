"""Unit tests for AgentDefaultsMixin."""

from pathlib import Path

import pytest

from src.api.v1.nodes.mixins import AgentDefaultsMixin
from src.state import AgentResult, FileAction, FileChange


class TestAgentDefaultsMixin:
    """Test suite for AgentDefaultsMixin."""

    @pytest.fixture
    def mixin_instance(self):
        """Create an instance of AgentDefaultsMixin for testing."""
        return AgentDefaultsMixin()

    def test_validate_input_returns_true_by_default(self, mixin_instance):
        """Test that validate_input returns True by default."""
        assert mixin_instance.validate_input({}) is True
        assert mixin_instance.validate_input({"key": "value"}) is True
        assert mixin_instance.validate_input({"nested": {"data": "value"}}) is True

    def test_validate_vault_path_with_valid_directory(self, mixin_instance, tmp_path):
        """Test vault path validation with valid directory."""
        vault = tmp_path / "vault"
        vault.mkdir()

        assert mixin_instance._validate_vault_path(vault) is True

    def test_validate_vault_path_with_nonexistent_path(self, mixin_instance):
        """Test vault path validation with nonexistent path."""
        nonexistent = Path("/nonexistent/path/to/vault")

        assert mixin_instance._validate_vault_path(nonexistent) is False

    def test_validate_vault_path_with_file_instead_of_directory(
        self, mixin_instance, tmp_path
    ):
        """Test vault path validation with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        assert mixin_instance._validate_vault_path(file_path) is False

    def test_create_success_result_with_defaults(self, mixin_instance):
        """Test creating success result with default parameters."""
        result = mixin_instance._create_success_result("Success message")

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.message == "Success message"
        assert result.changes == []
        assert result.metadata == {}

    def test_create_success_result_with_changes(self, mixin_instance):
        """Test creating success result with file changes."""
        changes = [
            FileChange("test.md", FileAction.CREATE, "content"),
            FileChange("update.md", FileAction.UPDATE, "new content"),
        ]

        result = mixin_instance._create_success_result("Created files", changes=changes)

        assert result.success is True
        assert len(result.changes) == 2
        assert result.changes[0].path == "test.md"

    def test_create_success_result_with_metadata(self, mixin_instance):
        """Test creating success result with metadata."""
        metadata = {"files_processed": 5, "categories": ["Programming"]}

        result = mixin_instance._create_success_result(
            "Processing complete", metadata=metadata
        )

        assert result.success is True
        assert result.metadata["files_processed"] == 5
        assert "Programming" in result.metadata["categories"]

    def test_create_failure_result_with_defaults(self, mixin_instance):
        """Test creating failure result with default parameters."""
        result = mixin_instance._create_failure_result("Operation failed")

        assert isinstance(result, AgentResult)
        assert result.success is False
        assert result.message == "Operation failed"
        assert result.changes == []
        assert isinstance(result.metadata, dict)

    def test_create_failure_result_with_exception(self, mixin_instance):
        """Test creating failure result with exception."""
        error = ValueError("Invalid input")

        result = mixin_instance._create_failure_result("Validation failed", error=error)

        assert result.success is False
        assert result.metadata["error"] == "Invalid input"
        assert result.metadata["error_type"] == "ValueError"

    def test_create_failure_result_with_metadata(self, mixin_instance):
        """Test creating failure result with custom metadata."""
        metadata = {"attempted_files": 10, "failed_at": 5}

        result = mixin_instance._create_failure_result(
            "Partial failure", metadata=metadata
        )

        assert result.success is False
        assert result.metadata["attempted_files"] == 10
        assert result.metadata["failed_at"] == 5
