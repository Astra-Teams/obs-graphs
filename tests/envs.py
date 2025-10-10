import pytest

@pytest.fixture(autouse=True)
def set_test_environment_variables(monkeypatch):
    """
    Set mock-related environment variables for test execution.
    This fixture is automatically enabled for all tests.
    """
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")