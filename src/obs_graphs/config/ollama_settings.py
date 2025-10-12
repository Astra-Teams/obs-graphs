"""Settings for configuring the Ollama backend."""

from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaSettings(BaseSettings):
    """Configuration values required to interact with an Ollama server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    model: str = Field(
        default="llama3.2:3b",
        description="Default Ollama model to use when generating completions.",
        alias="OBS_GRAPHS_OLLAMA_MODEL",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the Ollama REST API (e.g. http://localhost:11434/).",
        alias="OLLAMA_HOST",
    )
    request_timeout_seconds: float = Field(
        default=120.0,
        description="HTTP timeout (in seconds) when calling the Ollama REST API.",
        alias="OLLAMA_REQUEST_TIMEOUT_SECONDS",
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: Any) -> Optional[str]:
        """Normalize the base URL by trimming whitespace and ensuring trailing slash."""
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                return None
            return trimmed.rstrip("/") + "/"
        return value
