"""Unit tests for state module (FileAction, FileChange, NodeResult)."""

import pytest

from src.obs_glx.graphs.article_proposal.state import (
    FileAction,
    FileChange,
    NodeResult,
)


class TestFileAction:
    """Test the FileAction enum."""

    def test_file_action_values(self):
        """Test that FileAction has correct values."""
        assert FileAction.CREATE.value == "create"
        assert FileAction.UPDATE.value == "update"
        assert FileAction.DELETE.value == "delete"

    def test_file_action_members(self):
        """Test that FileAction has all expected members."""
        actions = [action.value for action in FileAction]
        assert "create" in actions
        assert "update" in actions
        assert "delete" in actions
        assert len(actions) == 3


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

    def test_file_change_equality(self):
        """Test that FileChange instances can be compared."""
        change1 = FileChange("test.md", FileAction.CREATE, "content")
        change2 = FileChange("test.md", FileAction.CREATE, "content")
        assert change1 == change2

    def test_file_change_different_paths(self):
        """Test that FileChanges with different paths are not equal."""
        change1 = FileChange("test1.md", FileAction.CREATE, "content")
        change2 = FileChange("test2.md", FileAction.CREATE, "content")
        assert change1 != change2


class TestNodeResult:
    """Test the NodeResult dataclass."""

    def test_successful_node_result(self):
        """Test creating a successful NodeResult."""
        changes = [FileChange("test.md", FileAction.CREATE, "content")]
        result = NodeResult(
            success=True,
            changes=changes,
            message="Created new article",
            metadata={"count": 1},
        )
        assert result.success is True
        assert len(result.changes) == 1
        assert result.message == "Created new article"
        assert result.metadata == {"count": 1}

    def test_failed_node_result(self):
        """Test creating a failed NodeResult."""
        result = NodeResult(
            success=False,
            changes=[],
            message="Failed to create article",
            metadata={"error": "timeout"},
        )
        assert result.success is False
        assert len(result.changes) == 0
        assert result.message == "Failed to create article"
        assert "error" in result.metadata

    def test_node_result_with_empty_changes(self):
        """Test NodeResult with empty changes list."""
        result = NodeResult(
            success=True, changes=[], message="No changes needed", metadata={}
        )
        assert result.success is True
        assert len(result.changes) == 0

    def test_node_result_with_multiple_changes(self):
        """Test NodeResult with multiple file changes."""
        changes = [
            FileChange("test1.md", FileAction.CREATE, "content1"),
            FileChange("test2.md", FileAction.UPDATE, "content2"),
            FileChange("test3.md", FileAction.DELETE, None),
        ]
        result = NodeResult(
            success=True,
            changes=changes,
            message="Multiple operations completed",
            metadata={"operations": 3},
        )
        assert len(result.changes) == 3
        assert result.metadata["operations"] == 3

    def test_node_result_default_metadata(self):
        """Test that NodeResult has default empty metadata."""
        result = NodeResult(success=True, changes=[], message="Test")
        assert isinstance(result.metadata, dict)
        assert len(result.metadata) == 0
