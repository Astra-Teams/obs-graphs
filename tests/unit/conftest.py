"""Unit test specific fixtures."""

import pytest

from tests.envs import setup_unit_test_env


@pytest.fixture(autouse=True)
def set_unit_test_env(monkeypatch):
    """Setup environment variables for unit tests."""
    setup_unit_test_env(monkeypatch)
