"""Environment variable configuration for different test categories."""


def setup_unit_test_env(monkeypatch):
    """Setup environment variables for unit tests."""
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")


def setup_intg_test_env(monkeypatch):
    """Setup environment variables for integration tests - all mocked."""
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")


def setup_e2e_test_env(monkeypatch):
    """Setup environment variables for E2E tests - use real services."""
    monkeypatch.setenv("USE_SQLITE", "false")
    monkeypatch.setenv("USE_MOCK_GITHUB", "false")
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("USE_MOCK_REDIS", "false")  # E2E uses real Redis
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "false")


def setup_db_test_env(monkeypatch):
    """Setup environment variables for database tests."""
    # monkeypatch.setenv("USE_SQLITE", "false")  # Commented out to allow db switching tests
    monkeypatch.setenv("USE_MOCK_GITHUB", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_REDIS", "true")
    monkeypatch.setenv("USE_MOCK_OLLAMA_DEEP_RESEARCHER", "true")
    monkeypatch.setenv("OBS_GRAPHS_OLLAMA_MODEL", "tinyllama:1.1b")
    monkeypatch.setenv("RESEARCH_API_OLLAMA_MODEL", "tinyllama:1.1b")
