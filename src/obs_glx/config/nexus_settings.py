"""Configuration for Nexus API integration."""

from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    """Settings for Nexus API configuration."""

    SUPPORTED_BACKENDS: ClassVar[tuple[str, ...]] = ("ollama", "mlx")

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
        normalized = str(value).strip().lower()
        if normalized not in cls.SUPPORTED_BACKENDS:
            supported = ", ".join(cls.SUPPORTED_BACKENDS)
            raise ValueError(
                f"Unsupported Nexus backend '{value}'. Supported backends: {supported}."
            )
        return normalized

    def resolve_backend(self, backend: str | None = None) -> str:
        """Resolve the effective backend, validating overrides when provided."""

        if backend is None:
            return self.nexus_default_backend
        normalized = str(backend).strip().lower()
        if normalized not in self.SUPPORTED_BACKENDS:
            supported = ", ".join(self.SUPPORTED_BACKENDS)
            raise ValueError(
                f"Unsupported Nexus backend '{backend}'. Supported backends: {supported}."
            )
        return normalized
