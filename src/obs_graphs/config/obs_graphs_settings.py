"""Main application configuration for the obs-graphs project."""

from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .db_settings import DBSettings
from .redis_settings import RedisSettings
from .research_api_settings import ResearchAPISettings


class ObsGraphsSettings(BaseSettings):
    """The configurable fields for the obs-graphs application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    DEBUG: bool = Field(
        default=False,
        title="Debug Mode",
        description="Enable mock client mode for development and testing.",
        alias="OBS_GRAPHS_DEBUG_MODE",
    )
    secret_key: str = Field(
        default="your-secret-key",
        title="Secret Key",
        description="A secret key for signing session data.",
        alias="OBS_GRAPHS_API_SECRET_KEY",
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
    use_mock_ollama_deep_researcher: bool = Field(
        default=True,
        title="Use Mock Ollama Deep Researcher",
        description="Return a mocked ollama deep researcher client when enabled.",
        alias="USE_MOCK_OLLAMA_DEEP_RESEARCHER",
    )

    # --- LLM Settings ---
    llm_model: str = Field(
        default="llama3.2:3b",
        title="LLM Model Name",
        description="Name of the LLM model to use.",
        alias="OBS_GRAPHS_OLLAMA_MODEL",
    )
    ollama_host: Optional[str] = Field(
        default=None,
        title="Ollama Base URL",
        description="Base URL for the Ollama API.",
        alias="OLLAMA_HOST",
    )

    # --- Database and Redis Settings ---
    db_settings: DBSettings = Field(default_factory=DBSettings)
    redis_settings: RedisSettings = Field(default_factory=RedisSettings)
    research_api_settings: ResearchAPISettings = Field(
        default_factory=ResearchAPISettings
    )

    # --- GitHub Integration ---
    github_token: str = Field(
        default="",
        title="GitHub Token",
        description="Personal Access Token for GitHub API.",
        alias="OBSIDIAN_VAULT_GITHUB_TOKEN",
    )

    github_repository: str = Field(
        default="Astra-Teams/constellations",
        title="GitHub Repository",
        description="The target repository for creating pull requests.",
        alias="OBSIDIAN_VAULT_REPOSITORY",
    )
    github_api_timeout_seconds: int = Field(
        default=30,
        title="GitHub API Timeout",
        description="Timeout in seconds for GitHub API requests.",
        alias="VAULT_GITHUB_API_TIMEOUT_SECONDS",
    )
    vault_submodule_path: str = Field(
        default="src/submodules/obsidian-vault",
        title="Vault Submodule Path",
        description="Filesystem path to the locally checked out Obsidian vault submodule.",
        alias="VAULT_SUBMODULE_PATH",
    )

    # --- Workflow Settings ---
    workflow_temp_dir_cleanup_seconds: int = Field(
        default=86400,
        title="Workflow Temp Directory Cleanup Interval",
        description="Number of seconds before temporary workflow directories are removed.",
        alias="WORKFLOW_TEMP_DIR_CLEANUP_SECONDS",
    )
    workflow_default_branch: str = Field(
        default="main",
        title="Workflow Default Branch",
        description="The default branch to use as the base for pull requests.",
        alias="WORKFLOW_DEFAULT_BRANCH",
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
