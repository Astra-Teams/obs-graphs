"""Mock obs-gtwy gateway client for offline development and testing."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_mock_research_client():
    """Dynamically load the mock research client from the olm-d-rch submodule."""

    project_root = Path(__file__).resolve().parents[2]
    client_path = (
        project_root
        / "src"
        / "submodules"
        / "olm-d-rch"
        / "sdk"
        / "mock_olm_d_rch_client"
        / "mock_olm_d_rch_client.py"
    )

    spec = importlib.util.spec_from_file_location("mock_olm_d_rch_client", client_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load mock_olm_d_rch_client module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MockOlmDRchClient


class MockObsGatewayClient:
    """Simple mock that fabricates obs-gtwy responses for tests."""

    def __init__(self) -> None:
        self._mock_client_cls = _load_mock_research_client()
        self._research_client = self._mock_client_cls()

    def create_draft_branch(
        self, *, file_name: str, content: str, branch_name: str
    ) -> str:
        """Return a deterministic branch name without touching GitHub."""

        if branch_name:
            return branch_name

        mock_result = self._research_client.research(file_name)
        _ = mock_result  # Diagnostics unused in mock branch generation

        slug = Path(file_name).stem.replace(" ", "-").lower()
        if not slug:
            slug = "draft"

        return f"draft/{slug}"
