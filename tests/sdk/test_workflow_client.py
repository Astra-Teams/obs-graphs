"""Unit-like tests for the obs_graphs_sdk workflow client module."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

import pytest

_sdk = import_module("obs_graphs_sdk")
WorkflowApiClient = _sdk.WorkflowApiClient
WorkflowRequest = _sdk.WorkflowRequest
MockWorkflowApiClient = _sdk.MockWorkflowApiClient


def _serialize(model):
    return model.model_dump()


@dataclass
class _DummyResponse:
    payload: dict[str, object]

    def raise_for_status(self) -> None:  # pragma: no cover - no exception expected
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class _DummyHttpClient:
    def __init__(self, response_payload: dict[str, object]) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self._response_payload = response_payload

    def post(self, url: str, json: dict[str, object]) -> _DummyResponse:
        self.calls.append((url, json))
        return _DummyResponse(self._response_payload)


def test_workflow_api_client_run_workflow_success():
    expected_response = {
        "id": 42,
        "status": "PENDING",
        "message": "queued",
        "celery_task_id": "abc123",
    }
    http_client = _DummyHttpClient(expected_response)

    client = WorkflowApiClient(
        base_url="http://example.com",
        client=http_client,  # Inject dummy client for deterministic testing
    )
    payload = WorkflowRequest(
        prompts=["Draft an outline"],
        strategy="article-proposal",
        async_execution=True,
    )

    response = client.run_workflow("article-proposal", payload)

    assert http_client.calls == [
        ("/api/workflows/article-proposal/run", _serialize(payload))
    ]
    assert response.model_dump() == expected_response


def test_mock_workflow_api_client_records_calls():
    mock_client = MockWorkflowApiClient()
    payload = WorkflowRequest(prompts=["Test prompt"])

    response = mock_client.run_workflow("article-proposal", payload)

    assert response.status == "COMPLETED"
    assert len(mock_client.call_history) == 1
    recorded_call = mock_client.call_history[0]
    assert recorded_call["workflow_name"] == "article-proposal"
    assert recorded_call["payload"] == payload


def test_workflow_request_requires_prompt():
    with pytest.raises(ValueError):
        WorkflowRequest(prompts=[])
