"""Configuration for Nexus API integration."""

from typing import ClassVar

from nexus_sdk.nexus_client import NexusMLXClient, NexusOllamaClient
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    """Settings for Nexus API configuration."""

    REAL_NEXUS_CLIENTS: ClassVar[dict[str, type]] = {
        "ollama": NexusOllamaClient,
        "mlx": NexusMLXClient,
    }
    SUPPORTED_BACKENDS: ClassVar[tuple[str, ...]] = tuple(
        sorted(REAL_NEXUS_CLIENTS.keys())
    )

    @classmethod
    def _normalize_and_validate_backend(cls, value: str) -> str:
        """Shared utility to normalize and validate a backend identifier."""
        normalized = str(value).strip().lower()
        if normalized not in cls.SUPPORTED_BACKENDS:
            supported = ", ".join(cls.SUPPORTED_BACKENDS)
            raise ValueError(
                f"Unsupported Nexus backend '{value}'. Supported backends: {supported}."
            )
        return normalized

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    nexus_base_url: str = Field(
        default="http://localhost:8000",
        title="Nexus Base URL",
        description="Base URL for the Nexus API",
        alias="NEXUS_BASE_URL",
    )
    nexus_timeout: float = Field(
        default=30.0,
        title="Nexus Timeout",
        description="Request timeout in seconds for Nexus API calls",
        alias="NEXUS_TIMEOUT",
    )
    use_mock_nexus: bool = Field(
        default=False,
        title="Use Mock Nexus Client",
        description="Use the mock Nexus client instead of the real implementation",
        alias="OBS_GLX_USE_MOCK_NEXUS",
    )
    nexus_default_backend: str = Field(
        default="ollama",
        title="Default Nexus Backend",
        description="Default LLM backend to target via Nexus (ollama or mlx)",
        alias="NEXUS_DEFAULT_BACKEND",
    )

    @field_validator("nexus_default_backend", mode="before")
    @classmethod
    def _validate_backend(cls, value: str | None) -> str:
        if value is None:
            return "ollama"
        return cls._normalize_and_validate_backend(value)

    def resolve_backend(self, backend: str | None = None) -> str:
        """Resolve the effective backend, validating overrides when provided."""
        if backend is None:
            return self.nexus_default_backend
        return self._normalize_and_validate_backend(backend)
