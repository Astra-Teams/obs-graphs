"""Gateway service configuration."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Configuration for the nexus gateway client."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    base_url: HttpUrl = Field(
        default="http://nexus-api:8000",
        alias="OBS_GTWY_API_URL",
        description="Base URL for the nexus API.",
    )
