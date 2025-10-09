"""Application configuration for the obs-graphs project."""

from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The configurable fields for the obs-graphs application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Core Settings ---
    DEBUG: bool = Field(
        default=False,
        title="Debug Mode",
        description="Enable mock client mode for development and testing.",
        alias="DEBUG",
    )
    secret_key: str = Field(
        default="your-secret-key",
        title="Secret Key",
        description="A secret key for signing session data.",
        alias="SECRET_KEY",
    )

    # --- Service Toggles ---
    use_sqlite: bool = Field(
        default=True,
        title="Use SQLite",
        description="Toggle between SQLite (True) and PostgreSQL (False) databases.",
        alias="USE_SQLITE",
    )
    use_mock_github: bool = Field(
        default=False,
        title="Use Mock GitHub",
        description="Return a mocked GitHub client when enabled.",
        alias="USE_MOCK_GITHUB",
    )
    use_mock_llm: bool = Field(
        default=False,
        title="Use Mock LLM",
        description="Return a mocked LLM client when enabled.",
        alias="USE_MOCK_LLM",
    )
    use_mock_redis: bool = Field(
        default=False,
        title="Use Mock Redis",
        description="Return a mocked Redis client when enabled.",
        alias="USE_MOCK_REDIS",
    )
    use_mock_research_api: bool = Field(
        default=False,
        title="Use Mock Research API",
        description="Return a mocked research API client when enabled.",
        alias="USE_MOCK_RESEARCH_API",
    )

    # --- LLM Settings ---
    llm_model: str = Field(
        default="llama3:8b",
        title="LLM Model Name",
        description="Name of the LLM model to use.",
        alias="OLLAMA_MODEL",
    )
    ollama_host: Optional[str] = Field(
        default=None,
        title="Ollama Base URL",
        description="Base URL for the Ollama API.",
        alias="OLLAMA_HOST",
    )

    # --- Database Settings ---
    database_url: str = Field(
        default="postgresql://user:password@db:5432/obs_graphs_db",
        title="Database URL",
        description="Database connection string for SQLAlchemy.",
        alias="DATABASE_URL",
    )

    # --- Redis Settings ---
    redis_host: str = Field(
        default="redis",
        title="Redis Host",
        description="Hostname for the Redis server.",
        alias="REDIS_HOST",
    )
    redis_port: int = Field(
        default=6379,
        title="Redis Port",
        description="Port number for the Redis server.",
        alias="REDIS_PORT",
    )
    celery_broker_url: str = Field(
        default="redis://redis:6379/0",
        title="Celery Broker URL",
        description="Connection string for the Celery message broker.",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://redis:6379/0",
        title="Celery Result Backend",
        description="Connection string for the Celery result backend.",
        alias="CELERY_RESULT_BACKEND",
    )

    # --- GitHub Integration ---
    github_token: str = Field(
        default="",
        title="GitHub Token",
        description="Personal Access Token for GitHub API.",
        alias="GITHUB_TOKEN",
    )
    github_repository: str = Field(
        default="your-username/your-repo",
        title="GitHub Repository",
        description="The target repository for creating pull requests.",
        alias="GITHUB_REPOSITORY",
    )
    github_api_timeout_seconds: int = Field(
        default=30,
        title="GitHub API Timeout",
        description="Timeout in seconds for GitHub API requests.",
        alias="GITHUB_API_TIMEOUT_SECONDS",
    )

    # --- Workflow Settings ---
    workflow_default_branch: str = Field(
        default="main",
        title="Workflow Default Branch",
        description="Default branch used when creating pull requests.",
        alias="WORKFLOW_DEFAULT_BRANCH",
    )
    workflow_clone_base_path: str = Field(
        default="/tmp/obs_graphs",
        title="Workflow Clone Base Path",
        description="Directory used to clone repositories during workflow execution.",
        alias="WORKFLOW_CLONE_BASE_PATH",
    )
    workflow_temp_dir_cleanup_seconds: int = Field(
        default=86400,
        title="Workflow Temp Directory Cleanup Interval",
        description="Number of seconds before temporary workflow directories are removed.",
        alias="WORKFLOW_TEMP_DIR_CLEANUP_SECONDS",
    )
    cross_reference_min_shared_keywords: int = Field(
        default=2,
        title="Cross Reference Minimum Shared Keywords",
        description="Minimum number of shared keywords required to cross reference notes.",
        alias="CROSS_REFERENCE_MIN_SHARED_KEYWORDS",
    )
    max_new_articles_per_run: int = Field(
        default=3,
        title="Maximum New Articles Per Run",
        description="Maximum number of new articles to propose during a workflow run.",
        alias="MAX_NEW_ARTICLES_PER_RUN",
    )
    api_max_page_size: int = Field(
        default=100,
        title="API Maximum Page Size",
        description="Maximum number of results that can be returned per API page.",
        alias="API_MAX_PAGE_SIZE",
    )

    # --- Research API ---
    research_api_url: str = Field(
        default="http://ollama-deep-researcher:8000/research",
        title="Research API URL",
        description="URL for the deep research API endpoint.",
        alias="RESEARCH_API_URL",
    )
    research_api_timeout_seconds: float = Field(
        default=300.0,
        title="Research API Timeout",
        description="Timeout in seconds for research API requests.",
        alias="RESEARCH_API_TIMEOUT_SECONDS",
    )

    @field_validator("ollama_host", mode="before")
    @classmethod
    def normalize_ollama_host(cls, value: Any) -> Any:
        """Normalize ollama_host by trimming whitespace and ensuring trailing slash."""
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                return None
            return trimmed.rstrip("/") + "/"
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        """Ensure DEBUG is parsed as a boolean from string."""
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "on"}
        return bool(value)


# Singleton instance for easy access across the application
settings = Settings()


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings
