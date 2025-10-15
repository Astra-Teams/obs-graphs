"""Configuration for Stella Connector API integration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StlConnSettings(BaseSettings):
    """Settings for Stella Connector API configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    stl_conn_base_url: str = Field(
        default="http://localhost:8000",
        title="Stella Connector Base URL",
        description="Base URL for the Stella Connector API",
        alias="STL_CONN_BASE_URL",
    )
    stl_conn_timeout: float = Field(
        default=30.0,
        title="Stella Connector Timeout",
        description="Request timeout in seconds for Stella Connector API calls",
        alias="STL_CONN_TIMEOUT",
    )
    use_mock_stl_conn: bool = Field(
        default=False,
        title="Use Mock Stella Connector Client",
        description="Use the mock Stella Connector client instead of the real implementation",
        alias="OBS_GLX_USE_MOCK_STL_CONN",
    )
