"""Workflow-specific settings for the obs-graphs project."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkflowSettings(BaseSettings):
    """Workflow execution configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    temp_dir_cleanup_seconds: int = Field(
        default=86400,
        title="Workflow Temp Directory Cleanup Interval",
        description="Number of seconds before temporary workflow directories are removed.",
        alias="WORKFLOW_TEMP_DIR_CLEANUP_SECONDS",
    )
    default_branch: str = Field(
        default="main",
        title="Workflow Default Branch",
        description="Base branch reference used when preparing draft submissions.",
        alias="WORKFLOW_DEFAULT_BRANCH",
    )
