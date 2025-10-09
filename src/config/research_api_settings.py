"""Research API-specific settings for the obs-graphs project."""

import os
from typing import Any

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ResearchAPISettings(BaseSettings):
    """Research API configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    research_api_url_default: str = Field(
        default="http://ollama-deep-researcher:8000/research",
        title="Research API URL Default",
        description="Default URL for the deep research API endpoint.",
    )
    research_api_timeout_seconds_default: float = Field(
        default=300.0,
        title="Research API Timeout Default",
        description="Default timeout in seconds for research API requests.",
    )

    @computed_field
    @property
    def research_api_url(self) -> str:
        """Get research API URL from environment or use default."""
        return os.getenv("RESEARCH_API_URL", self.research_api_url_default)

    @computed_field
    @property
    def research_api_timeout_seconds(self) -> float:
        """Get research API timeout from environment or use default."""
        return float(
            os.getenv(
                "RESEARCH_API_TIMEOUT_SECONDS",
                str(self.research_api_timeout_seconds_default),
            )
        )

    @field_validator("research_api_timeout_seconds_default", mode="before")
    @classmethod
    def validate_research_api_timeout(cls, value: Any) -> float:
        """Ensure research_api_timeout_seconds is a float."""
        if isinstance(value, str):
            return float(value)
        return value
