"""Configuration for Nexus API integration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    """Settings for Nexus API configuration."""

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
