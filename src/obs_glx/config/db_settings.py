"""Database-specific settings for the obs-graphs project."""

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    user: str = Field(
        default="user",
        validation_alias=AliasChoices("POSTGRES_USER", "user"),
        title="Database User",
        description="Username for the database connection.",
    )
    password: str = Field(
        default="password",
        validation_alias=AliasChoices("POSTGRES_PASSWORD", "password"),
        title="Database Password",
        description="Password for the database connection.",
    )
    host: str = Field(
        default="db",
        validation_alias=AliasChoices("POSTGRES_HOST", "host"),
        title="Database Host",
        description="Hostname for the database server.",
    )
    port: int = Field(
        default=5432,
        validation_alias=AliasChoices("POSTGRES_PORT", "port"),
        title="Database Port",
        description="Port number for the database server.",
    )
    db: str = Field(
        default="obs-graph-prod",
        validation_alias=AliasChoices("POSTGRES_DB", "db"),
        title="Database Name",
        description="Name of the database to connect to.",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Assemble the database URL from individual components."""
        url = f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        return url
