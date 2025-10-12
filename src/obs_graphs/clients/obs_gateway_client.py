"""HTTP client for interacting with the obs-gtwy gateway service."""

from __future__ import annotations

from typing import Final

import httpx

from src.obs_graphs.protocols import GatewayClientProtocol


class ObsGatewayClient(GatewayClientProtocol):
    """Synchronous HTTP client wrapper around the obs-gtwy draft endpoint."""

    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self._base_url: Final[str] = str(base_url).rstrip("/")
        self._timeout: Final[float] = timeout_seconds

    def create_draft_branch(
        self, *, file_name: str, content: str, branch_name: str
    ) -> str:
        """Create a branch via obs-gtwy and return the registered branch name."""

        payload = {
            "file_name": file_name,
            "content": content,
        }
        if branch_name:
            payload["branch_name"] = branch_name

        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
            ) as client:
                response = client.post("/drafts", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failures mocked
            raise RuntimeError(
                f"Failed to create draft branch via obs-gtwy: {exc}"
            ) from exc

        data = response.json()
        returned_branch = data.get("branch_name")
        if not isinstance(returned_branch, str) or not returned_branch.strip():
            raise RuntimeError(
                "obs-gtwy response missing branch_name field or contained invalid value."
            )

        return returned_branch.strip()
