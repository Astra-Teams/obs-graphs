from functools import lru_cache

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings


class ObsGraphsSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class loads configuration values used throughout the application from
    environment variables. Since Docker Compose automatically loads the .env file
    from the project root, there's no need to explicitly specify the file path.
    """

    # Mock/Real service switching flags
    USE_SQLITE: bool = True
    USE_MOCK_GITHUB: bool = False
    USE_MOCK_LLM: bool = False
    USE_MOCK_REDIS: bool = False
    USE_MOCK_RESEARCH_API: bool = False

    # PostgreSQL settings
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = ""

    # GitHub Authentication
    VAULT_GITHUB_TOKEN: str = ""
    OBSIDIAN_VAULT_REPO_FULL_NAME: str = ""

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Workflow Configuration
    WORKFLOW_DEFAULT_BRANCH: str = "main"
    WORKFLOW_TEMP_DIR_CLEANUP_SECONDS: int = 86400
    GITHUB_API_TIMEOUT_SECONDS: int = 30

    # Agent Configuration
    CROSS_REFERENCE_MIN_SHARED_KEYWORDS: int = 2
    MAX_NEW_ARTICLES_PER_RUN: int = 3

    # API Configuration
    API_MAX_PAGE_SIZE: int = 100

    # LLM Configuration
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Research API Configuration
    RESEARCH_API_BASE_URL: str = "http://ollama-deep-researcher:8000"
    RESEARCH_API_TIMEOUT_SECONDS: float = 300.0
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    @model_validator(mode="after")
    def _check_postgres_db(self) -> "ObsGraphsSettings":
        """Validate that POSTGRES_DB is set when using PostgreSQL."""
        if not self.USE_SQLITE and not self.POSTGRES_DB:
            raise ValueError("POSTGRES_DB must be set when USE_SQLITE is False.")
        return self

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Return PostgreSQL database URL. Switching logic is in database.py."""
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache
def get_settings() -> ObsGraphsSettings:
    return ObsGraphsSettings()
