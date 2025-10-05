from functools import lru_cache
from pathlib import Path

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings


class ObsGraphsSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class loads configuration values used throughout the application from
    environment variables. Since Docker Compose automatically loads the .env file
    from the project root, there's no need to explicitly specify the file path.
    """

    USE_SQLITE: bool = True

    # PostgreSQL settings
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = ""

    # GitHub App Authentication
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY_PATH: str = ""
    GITHUB_INSTALLATION_ID: str = ""
    GITHUB_REPO_FULL_NAME: str = ""

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Workflow Configuration
    WORKFLOW_CLONE_BASE_PATH: str = "/tmp/obsidian-workflows"
    WORKFLOW_DEFAULT_BRANCH: str = "main"

    # LLM Configuration
    OLLAMA_MODEL: str = "llama3.2:3b"

    @field_validator("GITHUB_APP_PRIVATE_KEY_PATH")
    @classmethod
    def _validate_private_key_path(cls, v: str) -> str:
        if v and not Path(v).exists():
            raise ValueError(f"GitHub App private key file not found: {v}")
        return v

    @model_validator(mode="after")
    def _check_postgres_db(self) -> "ObsGraphsSettings":
        if not self.USE_SQLITE and not self.POSTGRES_DB:
            raise ValueError("POSTGRES_DB must be set when USE_SQLITE is False.")
        return self

    @model_validator(mode="after")
    def _validate_github_app_credentials(self) -> "ObsGraphsSettings":
        github_fields = [
            self.GITHUB_APP_ID,
            self.GITHUB_APP_PRIVATE_KEY_PATH,
            self.GITHUB_INSTALLATION_ID,
            self.GITHUB_REPO_FULL_NAME,
        ]
        # If any GitHub App field is set, all must be set
        if any(github_fields) and not all(github_fields):
            raise ValueError(
                "All GitHub App credentials must be set: GITHUB_APP_ID, "
                "GITHUB_APP_PRIVATE_KEY_PATH, GITHUB_INSTALLATION_ID, GITHUB_REPO_FULL_NAME"
            )
        return self

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE:
            return "sqlite:///./test_db.sqlite3"
        else:
            return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache
def get_settings() -> ObsGraphsSettings:
    return ObsGraphsSettings()
