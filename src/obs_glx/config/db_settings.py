"""Database-specific settings for the obs-graphs project."""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_user: str = Field(
        default="user",
        title="Database User",
        description="Username for the database connection.",
        validation_alias="POSTGRES_USER",
    )
    db_password: str = Field(
        default="password",
        title="Database Password",
        description="Password for the database connection.",
        validation_alias="POSTGRES_PASSWORD",
    )
    db_host: str = Field(
        default="db",
        title="Database Host",
        description="Hostname for the database server.",
        validation_alias="POSTGRES_HOST",
    )
    db_port: int = Field(
        default=5432,
        title="Database Port",
        description="Port number for the database server.",
        validation_alias="POSTGRES_PORT",
    )
    db_name: str = Field(
        default="obs-graph-prod",
        title="Database Name",
        description="Name of the database to connect to.",
        validation_alias="POSTGRES_DB",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Assemble the database URL from individual components."""
        url = f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return url
