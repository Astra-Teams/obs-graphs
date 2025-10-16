"""GitHub integration helpers for creating draft branches directly."""

from __future__ import annotations

import base64
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

import httpx

from src.obs_glx.config.github_settings import GitHubSettings

Clock = Callable[[], datetime]

DEFAULT_PULL_REQUEST_BODY = "Posting a new draft article."
COMMIT_MESSAGE_TEMPLATE = "feat: Add draft '{file_name}'"


def _default_clock() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(timezone.utc)


class GitHubConfigurationError(RuntimeError):
    """Raised when required GitHub configuration values are missing."""


class GitHubAPIError(RuntimeError):
    """Raised when an error occurs while communicating with the GitHub API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubDraftServiceProtocol(Protocol):
    """Protocol for services that materialise drafts in GitHub."""

    async def create_draft_branch(
        self, *, drafts: Sequence[Mapping[str, str] | object]
    ) -> str:
        """Create a branch that contains the supplied drafts."""


@dataclass(slots=True)
class GitHubDraftService(GitHubDraftServiceProtocol):
    """High-level client that turns a draft into a GitHub branch."""

    owner: str
    repo: str
    base_branch: str
    token: str
    drafts_directory: str = "drafts"
    api_url: str = "https://api.github.com"
    api_version: str = "2022-11-28"
    pull_request_body: str = DEFAULT_PULL_REQUEST_BODY
    clock: Clock = field(default=_default_clock)

    def __post_init__(self) -> None:
        self.drafts_directory = self.drafts_directory.strip("/")
        if not self.drafts_directory:
            self.drafts_directory = "drafts"
        self.api_url = self.api_url.rstrip("/")

    @classmethod
    def from_settings(
        cls,
        settings: GitHubSettings,
        *,
        clock: Clock | None = None,
    ) -> GitHubDraftService:
        """Create a service instance from GitHub settings."""

        token_secret = settings.github_token
        if token_secret is None or not token_secret.get_secret_value():
            raise GitHubConfigurationError(
                "GitHub token is not configured. Set OBS_GLX_GITHUB_TOKEN."
            )

        owner = settings.github_repo_owner
        if not owner:
            raise GitHubConfigurationError(
                "GitHub repository owner is not configured. Set OBS_GLX_GITHUB_REPO in format 'owner/repo'."
            )

        repo = settings.github_repo_name
        if not repo:
            raise GitHubConfigurationError(
                "GitHub repository name is not configured. Set OBS_GLX_GITHUB_REPO in format 'owner/repo'."
            )

        base_branch = settings.github_base_branch or "main"

        return cls(
            owner=owner,
            repo=repo,
            base_branch=base_branch,
            token=token_secret.get_secret_value(),
            drafts_directory=settings.drafts_directory,
            api_url=str(settings.github_api_url),
            api_version=settings.github_api_version,
            clock=clock or _default_clock,
        )

    async def create_draft_branch(
        self,
        *,
        drafts: Sequence[Mapping[str, str] | object],
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """Create a branch that contains all supplied drafts."""

        if not drafts:
            raise GitHubAPIError(
                "At least one draft must be provided.", HTTPStatus.UNPROCESSABLE_ENTITY
            )

        sanitized: list[tuple[str, str]] = []
        for draft in drafts:
            file_name = self._extract_attr(draft, "file_name")
            content = self._extract_attr(draft, "content")
            if file_name is None or content is None:
                raise GitHubAPIError(
                    "Draft payload must include file_name and content.",
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                )
            safe_file_name = self._sanitize_file_name(str(file_name))
            sanitized.append((safe_file_name, str(content)))

        primary_file = sanitized[0][0]
        if len(sanitized) == 1:
            branch_source = primary_file
        else:
            stem = primary_file.rsplit(".", 1)[0]
            branch_source = f"{stem}-batch-{len(sanitized)}.md"

        branch_candidate = self._build_branch_name(branch_source)

        close_client = client is None
        http_client = client or httpx.AsyncClient(
            base_url=self.api_url,
            headers=self._build_headers(),
            timeout=30.0,
        )
        if client is not None:
            http_client.headers.update(self._build_headers())

        try:
            base_sha = await self._fetch_base_branch_sha(http_client)
            branch_name = await self._ensure_unique_branch(
                http_client, branch_candidate, base_sha
            )
            for safe_file_name, content in sanitized:
                commit_message = self._build_commit_message(safe_file_name)
                path = self._build_repository_path(safe_file_name)
                await self._create_file(
                    client=http_client,
                    repository_path=path,
                    branch_name=branch_name,
                    commit_message=commit_message,
                    content=content,
                )
        except httpx.RequestError as exc:
            raise GitHubAPIError("Failed to communicate with GitHub.") from exc
        finally:
            if close_client:
                await http_client.aclose()

        return branch_name

    def _extract_attr(self, draft: Mapping[str, str] | object, name: str) -> str | None:
        value = (
            draft.get(name)
            if isinstance(draft, Mapping)
            else getattr(draft, name, None)
        )
        if value is not None:
            return str(value)
        return None

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
        }

    def _sanitize_file_name(self, file_name: str) -> str:
        candidate = Path(file_name)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise GitHubAPIError(
                "Invalid draft filename supplied.",
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        sanitized = candidate.name
        if sanitized != file_name:
            raise GitHubAPIError(
                "Invalid draft filename supplied.", HTTPStatus.UNPROCESSABLE_ENTITY
            )
        if not sanitized:
            raise GitHubAPIError(
                "Invalid draft filename supplied.", HTTPStatus.UNPROCESSABLE_ENTITY
            )
        if sanitized.startswith(".") or "/" in sanitized or "\\" in sanitized:
            raise GitHubAPIError(
                "Invalid draft filename supplied.", HTTPStatus.UNPROCESSABLE_ENTITY
            )
        if not sanitized.lower().endswith(".md"):
            raise GitHubAPIError(
                "Draft filename must end with .md.", HTTPStatus.UNPROCESSABLE_ENTITY
            )

        return sanitized

    def _build_branch_name(self, file_name: str) -> str:
        timestamp = self.clock().strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(file_name)
        return f"drafts/{timestamp}-{slug}"

    def _build_commit_message(self, file_name: str) -> str:
        return COMMIT_MESSAGE_TEMPLATE.format(file_name=file_name)

    def _build_repository_path(self, file_name: str) -> str:
        return f"{self.drafts_directory}/{file_name}"

    def _build_pull_request_title(self, file_name: str) -> str:
        stem = file_name.rsplit(".", 1)[0]
        title = re.sub(r"[-_]+", " ", stem).strip()
        if not title:
            title = "New Draft"
        return title.title()

    def _slugify(self, file_name: str) -> str:
        stem = file_name.rsplit(".", 1)[0]
        slug = re.sub(r"[^a-z0-9]+", "-", stem.lower())
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        return slug or "draft"

    async def _fetch_base_branch_sha(self, client: httpx.AsyncClient) -> str:
        response = await client.get(
            f"/repos/{self.owner}/{self.repo}/git/ref/heads/{self.base_branch}"
        )
        self._raise_for_status(
            response, f"Failed to fetch branch '{self.base_branch}'."
        )

        data = response.json()
        try:
            return data["object"]["sha"]
        except (KeyError, TypeError) as exc:
            raise GitHubAPIError(
                "GitHub response missing base branch reference.", response.status_code
            ) from exc

    async def _ensure_unique_branch(
        self,
        client: httpx.AsyncClient,
        branch_name: str,
        base_sha: str,
    ) -> str:
        try:
            await self._create_branch(client, branch_name, base_sha)
            return branch_name
        except GitHubAPIError as exc:
            if exc.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                unique_branch = f"{branch_name}-{secrets.token_hex(3)}"
                await self._create_branch(client, unique_branch, base_sha)
                return unique_branch
            raise

    async def _create_branch(
        self,
        client: httpx.AsyncClient,
        branch_name: str,
        base_sha: str,
    ) -> None:
        response = await client.post(
            f"/repos/{self.owner}/{self.repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            message = (
                self._extract_error_message(response)
                or f"Branch '{branch_name}' already exists."
            )
            raise GitHubAPIError(message, response.status_code)
        self._raise_for_status(response, f"Failed to create branch '{branch_name}'.")

    async def _create_file(
        self,
        *,
        client: httpx.AsyncClient,
        repository_path: str,
        branch_name: str,
        commit_message: str,
        content: str,
    ) -> None:
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        response = await client.put(
            f"/repos/{self.owner}/{self.repo}/contents/{repository_path}",
            json={
                "message": commit_message,
                "content": encoded,
                "branch": branch_name,
            },
        )
        self._raise_for_status(response, f"Failed to create draft '{repository_path}'.")

    def _raise_for_status(self, response: httpx.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error_message(response)
            detail_text = (
                f"{message}" if not detail else f"{message} (GitHub: {detail})"
            )
            raise GitHubAPIError(detail_text, response.status_code) from exc

    def _extract_error_message(self, response: httpx.Response) -> str | None:
        try:
            body = response.json()
        except json.JSONDecodeError:
            text = response.text.strip()
            return text or None

        if isinstance(body, dict):
            message = body.get("message")
            errors = body.get("errors")
            extra = None
            if isinstance(errors, list):
                extra_messages: list[str] = []
                for error in errors:
                    if isinstance(error, dict) and "message" in error:
                        extra_messages.append(str(error["message"]))
                    elif isinstance(error, str):
                        extra_messages.append(error)
                if extra_messages:
                    extra = "; ".join(extra_messages)
            if message and extra:
                return f"{message}: {extra}"
            if extra:
                return extra
            return message
        return None


class MockGitHubDraftService(GitHubDraftServiceProtocol):
    """Mock GitHub service used for local development and tests."""

    async def create_draft_branch(
        self, *, drafts: Sequence[Mapping[str, str] | object]
    ) -> str:
        print(f"Mock GitHub draft service called with drafts: {drafts}")
        return "drafts/20250101-120000-mock-branch-name"
