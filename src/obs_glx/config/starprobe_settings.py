"""Starprobe-specific settings for the obs-graphs project."""

import os
from typing import Any

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StarprobeSettings(BaseSettings):
    """Starprobe configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    starprobe_api_url_default: str = Field(
        default="http://starprobe-api:8000/research",
        title="Starprobe API URL Default",
        description="Default URL for the Starprobe API endpoint.",
    )
    starprobe_api_timeout_seconds_default: float = Field(
        default=300.0,
        title="Starprobe API Timeout Default",
        description="Default timeout in seconds for Starprobe API requests.",
    )

    @computed_field
    @property
    def starprobe_api_url(self) -> str:
        """Get Starprobe API URL from environment or use default."""
        return os.getenv("STARPROBE_API_URL", self.starprobe_api_url_default)

    @computed_field
    @property
    def starprobe_api_timeout_seconds(self) -> float:
        """Get Starprobe API timeout from environment or use default."""
        return float(
            os.getenv(
                "STARPROBE_API_TIMEOUT_SECONDS",
                str(self.starprobe_api_timeout_seconds_default),
            )
        )

    @field_validator("starprobe_api_timeout_seconds_default", mode="before")
    @classmethod
    def validate_starprobe_api_timeout(cls, value: Any) -> float:
        """Ensure starprobe_api_timeout_seconds is a float."""
        if isinstance(value, str):
            return float(value)
        return value
