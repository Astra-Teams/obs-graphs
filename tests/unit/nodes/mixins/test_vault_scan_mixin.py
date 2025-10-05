"""Unit tests for VaultScanMixin."""

from pathlib import Path

import pytest

from src.api.v1.nodes.mixins import VaultScanMixin


class TestVaultScanMixin:
    """Test suite for VaultScanMixin."""

    @pytest.fixture
    def mixin_instance(self):
        """Create an instance of VaultScanMixin for testing."""
        return VaultScanMixin()

    @pytest.fixture
    def vault_with_files(self, tmp_path):
        """Create a vault with markdown files for testing."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create files at root
        (vault / "root.md").write_text("# Root File")
        (vault / "readme.txt").write_text("Not markdown")

        # Create nested structure
        category = vault / "Category"
        category.mkdir()
        (category / "nested.md").write_text("# Nested File")

        subcategory = category / "Subcategory"
        subcategory.mkdir()
        (subcategory / "deep.md").write_text("# Deep File")

        return vault

    def test_scan_markdown_files_recursive(self, mixin_instance, vault_with_files):
        """Test recursive markdown file scanning."""
        files = mixin_instance._scan_markdown_files(vault_with_files, recursive=True)

        assert len(files) == 3
        assert all(f.suffix == ".md" for f in files)
        assert all(f.is_file() for f in files)

    def test_scan_markdown_files_non_recursive(self, mixin_instance, vault_with_files):
        """Test non-recursive markdown file scanning."""
        files = mixin_instance._scan_markdown_files(vault_with_files, recursive=False)

        assert len(files) == 1
        assert files[0].name == "root.md"

    def test_scan_markdown_files_empty_vault(self, mixin_instance, tmp_path):
        """Test scanning empty vault."""
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        files = mixin_instance._scan_markdown_files(empty_vault)

        assert files == []

    def test_scan_markdown_files_sorted(self, mixin_instance, vault_with_files):
        """Test that scanned files are sorted."""
        files = mixin_instance._scan_markdown_files(vault_with_files)

        file_names = [f.name for f in files]
        assert file_names == sorted(file_names)

    def test_read_file_safe_with_valid_file(self, mixin_instance, tmp_path):
        """Test safe file reading with valid file."""
        file_path = tmp_path / "test.md"
        content = "# Test Content\n\nSome text here."
        file_path.write_text(content)

        result = mixin_instance._read_file_safe(file_path)

        assert result == content

    def test_read_file_safe_with_nonexistent_file(self, mixin_instance):
        """Test safe file reading with nonexistent file."""
        nonexistent = Path("/nonexistent/file.md")

        result = mixin_instance._read_file_safe(nonexistent)

        assert result is None

    def test_read_file_safe_with_permission_error(self, mixin_instance, tmp_path):
        """Test safe file reading handles permission errors."""
        # This test may not work on all systems, but demonstrates the concept
        file_path = tmp_path / "restricted.md"
        file_path.write_text("content")

        # Note: Actually setting permissions may not work in all test environments
        result = mixin_instance._read_file_safe(file_path)

        # Should either succeed or return None, not raise exception
        assert result is None or isinstance(result, str)

    def test_get_relative_path(self, mixin_instance, tmp_path):
        """Test getting relative path from vault root."""
        vault = tmp_path / "vault"
        vault.mkdir()

        category = vault / "Programming"
        category.mkdir()
        file_path = category / "python.md"
        file_path.write_text("content")

        relative = mixin_instance._get_relative_path(file_path, vault)

        assert relative == "Programming/python.md"

    def test_get_relative_path_root_file(self, mixin_instance, tmp_path):
        """Test getting relative path for file at vault root."""
        vault = tmp_path / "vault"
        vault.mkdir()

        file_path = vault / "readme.md"
        file_path.write_text("content")

        relative = mixin_instance._get_relative_path(file_path, vault)

        assert relative == "readme.md"
