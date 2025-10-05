"""Unit tests for state module (FileAction, FileChange, AgentResult)."""

import pytest

from src.state import AgentResult, FileAction, FileChange


class TestFileChange:
    """Test the FileChange dataclass."""

    def test_create_file_change_with_content(self):
        """Test creating a FileChange for CREATE action."""
        change = FileChange(
            path="test.md", action=FileAction.CREATE, content="# Test Content"
        )
        assert change.path == "test.md"
        assert change.action == FileAction.CREATE
        assert change.content == "# Test Content"

    def test_update_file_change_with_content(self):
        """Test creating a FileChange for UPDATE action."""
        change = FileChange(
            path="existing.md", action=FileAction.UPDATE, content="# Updated Content"
        )
        assert change.path == "existing.md"
        assert change.action == FileAction.UPDATE
        assert change.content == "# Updated Content"

    def test_delete_file_change_without_content(self):
        """Test creating a FileChange for DELETE action."""
        change = FileChange(path="old.md", action=FileAction.DELETE, content=None)
        assert change.path == "old.md"
        assert change.action == FileAction.DELETE
        assert change.content is None

    def test_create_without_content_raises_error(self):
        """Test that CREATE without content raises ValueError."""
        with pytest.raises(
            ValueError, match="Content must be provided for create action"
        ):
            FileChange(path="test.md", action=FileAction.CREATE, content=None)

    def test_update_without_content_raises_error(self):
        """Test that UPDATE without content raises ValueError."""
        with pytest.raises(
            ValueError, match="Content must be provided for update action"
        ):
            FileChange(path="test.md", action=FileAction.UPDATE, content=None)

    def test_delete_with_content_raises_error(self):
        """Test that DELETE with content raises ValueError."""
        with pytest.raises(
            ValueError, match="Content should not be provided for DELETE action"
        ):
            FileChange(
                path="test.md",
                action=FileAction.DELETE,
                content="Should not have content",
            )


class TestAgentResult:
    """Test the AgentResult dataclass."""

    def test_successful_agent_result(self):
        """Test creating a successful AgentResult."""
        changes = [FileChange("test.md", FileAction.CREATE, "content")]
        result = AgentResult(
            success=True,
            changes=changes,
            message="Created new article",
            metadata={"count": 1},
        )
        assert result.success is True
        assert len(result.changes) == 1
        assert result.message == "Created new article"
        assert result.metadata == {"count": 1}

    def test_failed_agent_result(self):
        """Test creating a failed AgentResult."""
        result = AgentResult(
            success=False,
            changes=[],
            message="Failed to create article",
            metadata={"error": "timeout"},
        )
        assert result.success is False
        assert len(result.changes) == 0
        assert result.message == "Failed to create article"
        assert "error" in result.metadata

    def test_agent_result_with_empty_changes(self):
        """Test AgentResult with empty changes list."""
        result = AgentResult(
            success=True, changes=[], message="No changes needed", metadata={}
        )
        assert result.success is True
        assert len(result.changes) == 0

    def test_agent_result_with_multiple_changes(self):
        """Test AgentResult with multiple file changes."""
        changes = [
            FileChange("test1.md", FileAction.CREATE, "content1"),
            FileChange("test2.md", FileAction.UPDATE, "content2"),
            FileChange("test3.md", FileAction.DELETE, None),
        ]
        result = AgentResult(
            success=True,
            changes=changes,
            message="Multiple operations completed",
            metadata={"operations": 3},
        )
        assert len(result.changes) == 3
        assert result.metadata["operations"] == 3

    def test_agent_result_default_metadata(self):
        """Test that AgentResult has default empty metadata."""
        result = AgentResult(success=True, changes=[], message="Test")
        assert isinstance(result.metadata, dict)
        assert len(result.metadata) == 0
