"""Database-specific settings for the obs-graphs project."""

import os

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    db_user: str = Field(
        default="user",
        title="Database User",
        description="Username for the database connection.",
        alias="DB_USER",
    )
    db_password: str = Field(
        default="password",
        title="Database Password",
        description="Password for the database connection.",
        alias="DB_PASSWORD",
    )
    db_host: str = Field(
        default="db",
        title="Database Host",
        description="Hostname for the database server.",
        alias="DB_HOST",
    )
    db_port: int = Field(
        default=5432,
        title="Database Port",
        description="Port number for the database server.",
        alias="DB_PORT",
    )
    db_name: str = Field(
        default="obs_graphs_db",
        title="Database Name",
        description="Name of the database to connect to.",
        alias="DB_NAME",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Assemble the database URL from individual components."""
        db_name = os.getenv("POSTGRES_DB", self.db_name)
        url = f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{db_name}"
        return url
