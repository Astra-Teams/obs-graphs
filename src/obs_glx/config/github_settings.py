"""GitHub-specific settings for obs-glx."""

from __future__ import annotations

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubSettings(BaseSettings):
    """Configuration values for GitHub API integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    github_token: SecretStr | None = Field(
        default=None,
        alias="OBS_GLX_GITHUB_TOKEN",
        description="Personal Access Token for GitHub API operations.",
    )
    github_repository: str | None = Field(
        default=None,
        alias="OBS_GLX_GITHUB_REPO",
        description="GitHub repository in format 'owner/repo'.",
    )
    github_base_branch: str = Field(
        default="main",
        alias="OBS_GLX_GITHUB_BASE_BRANCH",
        description="Base branch for creating draft branches.",
    )
    drafts_directory: str = Field(
        default="drafts",
        alias="OBS_GLX_DRAFTS_DIRECTORY",
        description="Directory where draft markdown files are stored in the repository.",
    )
    github_api_url: HttpUrl = Field(
        default="https://api.github.com",
        alias="OBS_GLX_GITHUB_API_URL",
        description="Base URL for the GitHub API.",
    )
    github_api_version: str = Field(
        default="2022-11-28",
        alias="OBS_GLX_GITHUB_API_VERSION",
        description="GitHub API version to use for requests.",
    )

    @property
    def github_repo_owner(self) -> str | None:
        """Return the owner portion of the repository."""

        if self.github_repository:
            return self.github_repository.split("/", 1)[0]
        return None

    @property
    def github_repo_name(self) -> str | None:
        """Return the repository name portion of the repository."""

        if self.github_repository:
            parts = self.github_repository.split("/", 1)
            return parts[1] if len(parts) == 2 else None
        return None
