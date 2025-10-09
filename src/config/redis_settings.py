"""Redis-specific settings for the obs-graphs project."""

import os
from typing import Any

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    redis_host_default: str = Field(
        default="redis",
        title="Redis Host Default",
        description="Default hostname for the Redis server.",
    )
    redis_port_default: int = Field(
        default=6379,
        title="Redis Port Default",
        description="Default port for the Redis server.",
    )

    @computed_field
    @property
    def redis_host(self) -> str:
        """Get Redis host from environment or use default."""
        return os.getenv("OBS_GRAPHS_REDIS_HOST", self.redis_host_default)

    @computed_field
    @property
    def redis_port(self) -> int:
        """Get Redis port from environment or use default."""
        return int(os.getenv("OBS_GRAPHS_REDIS_PORT", str(self.redis_port_default)))

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        """Assemble Celery broker URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @computed_field
    @property
    def celery_result_backend(self) -> str:
        """Assemble Celery result backend URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/1"

    @field_validator("redis_port_default", mode="before")
    @classmethod
    def validate_redis_port(cls, value: Any) -> int:
        """Ensure redis_port is an integer."""
        if isinstance(value, str):
            return int(value)
        return value
