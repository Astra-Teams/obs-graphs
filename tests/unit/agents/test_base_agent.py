"""Unit tests for base agent interface and utilities."""

from pathlib import Path

import pytest

from src.agents.base import AgentResult, BaseAgent, FileAction, FileChange


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


class TestBaseAgent:
    """Test the BaseAgent abstract class."""

    def test_cannot_instantiate_base_agent(self):
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent()

    def test_concrete_agent_must_implement_execute(self):
        """Test that concrete agents must implement execute method."""

        class IncompleteAgent(BaseAgent):
            def validate_input(self, context: dict) -> bool:
                return True

            def get_name(self) -> str:
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_concrete_agent_must_implement_validate_input(self):
        """Test that concrete agents must implement validate_input method."""

        class IncompleteAgent(BaseAgent):
            def execute(self, vault_path: Path, context: dict) -> AgentResult:
                return AgentResult(True, [], "test", {})

            def get_name(self) -> str:
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_concrete_agent_must_implement_get_name(self):
        """Test that concrete agents must implement get_name method."""

        class IncompleteAgent(BaseAgent):
            def execute(self, vault_path: Path, context: dict) -> AgentResult:
                return AgentResult(True, [], "test", {})

            def validate_input(self, context: dict) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_complete_concrete_agent(self):
        """Test that a complete concrete agent can be instantiated."""

        class CompleteAgent(BaseAgent):
            def execute(self, vault_path: Path, context: dict) -> AgentResult:
                return AgentResult(
                    success=True, changes=[], message="Test execution", metadata={}
                )

            def validate_input(self, context: dict) -> bool:
                return True

            def get_name(self) -> str:
                return "CompleteAgent"

        agent = CompleteAgent()
        assert agent.get_name() == "CompleteAgent"
        assert agent.validate_input({}) is True

        result = agent.execute(Path("/tmp"), {})
        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_agent_execute_signature(self):
        """Test that execute method has correct signature."""

        class TestAgent(BaseAgent):
            def execute(self, vault_path: Path, context: dict) -> AgentResult:
                assert isinstance(vault_path, Path)
                assert isinstance(context, dict)
                return AgentResult(True, [], "test", {})

            def validate_input(self, context: dict) -> bool:
                return True

            def get_name(self) -> str:
                return "TestAgent"

        agent = TestAgent()
        result = agent.execute(Path("/tmp/vault"), {"test": "data"})
        assert isinstance(result, AgentResult)
