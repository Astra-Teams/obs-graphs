"""Main application configuration for the obs-graphs project."""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObsGraphsSettings(BaseSettings):
    """The configurable fields for the obs-graphs application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    debug: bool = Field(
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
    api_max_page_size: int = Field(
        default=100,
        title="API Max Page Size",
        description="Maximum number of items to return in paginated API responses.",
        alias="API_MAX_PAGE_SIZE",
    )

    # --- Service Toggles ---
    use_sqlite: bool = Field(
        default=True,
        title="Use SQLite",
        description="Toggle between SQLite (True) and PostgreSQL (False) databases.",
        alias="USE_SQLITE",
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
    use_mock_obs_gateway: bool = Field(
        default=True,
        title="Use Mock nexus Gateway",
        description="Return a mocked nexus client when enabled.",
        alias="USE_MOCK_OBS_GTWY",
    )

    vault_submodule_path: str = Field(
        default="submodules/constellations",
        title="Vault Submodule Path",
        description="Filesystem path to the locally checked out Obsidian vault submodule.",
        alias="VAULT_SUBMODULE_PATH",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        """Ensure debug is parsed as a boolean from string."""
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "on"}
        return bool(value)
