"""Unit tests for API router prompt validation."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.obs_graphs.api.router import router
from src.obs_graphs.db.database import Base
from src.obs_graphs.db.models.workflow import Workflow
from src.obs_graphs.graphs.article_proposal.state import WorkflowStrategy

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override dependency to use test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create FastAPI test client with database override."""
    from unittest.mock import MagicMock

    from fastapi import FastAPI

    from src.obs_graphs import dependencies

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[dependencies.get_db_session] = override_get_db

    # Mock LLM client to avoid async issues in tests
    mock_llm_client = MagicMock()
    mock_llm_client.invoke.return_value = MagicMock()
    mock_llm_client.invoke.return_value.content = '{"test": "mock response"}'
    mock_llm_provider = MagicMock(return_value=mock_llm_client)
    app.dependency_overrides[dependencies.get_llm_client_provider] = (
        lambda: mock_llm_provider
    )

    return TestClient(app)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task to prevent actual task execution."""
    with patch("worker.obs_graphs_worker.tasks.run_workflow_task") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        mock_task.delay.return_value = mock_result
        yield mock_task


def test_workflow_run_with_valid_prompts(client, mock_celery_task):
    """Test that a list of prompts is accepted and persisted to the database."""

    payload = {
        "prompts": [
            "Research the impact of transformers on NLP",
            "Summarise the findings",
        ],
        "async_execution": True,
    }

    response = client.post("/api/workflows/article-proposal/run", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert {"id", "status"}.issubset(data)

    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow is not None
    assert workflow.prompt == [prompt.strip() for prompt in payload["prompts"]]


@pytest.mark.parametrize(
    "payload",
    [
        {"prompts": [], "async_execution": True},
        {"prompts": ["   "], "async_execution": False},
        {"prompts": ["Valid", "  "], "async_execution": True},
    ],
)
def test_workflow_run_rejects_invalid_prompt_lists(client, payload):
    """Prompt lists must be non-empty and contain only non-empty strings."""

    response = client.post("/api/workflows/article-proposal/run", json=payload)

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("prompts" in str(error).lower() for error in error_detail)


def test_workflow_run_rejects_missing_prompts(client):
    """Test that omitting the prompts field is rejected."""

    response = client.post(
        "/api/workflows/article-proposal/run",
        json={"async_execution": False},
    )

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("prompts" in str(error).lower() for error in error_detail)


def test_workflow_run_prompts_strip_whitespace(client, mock_celery_task):
    """Prompts should be normalised by stripping surrounding whitespace."""

    response = client.post(
        "/api/workflows/article-proposal/run",
        json={
            "prompts": ["  Research topic with spaces  ", " follow up on insights  "],
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == [
        "Research topic with spaces",
        "follow up on insights",
    ]


def test_workflow_run_with_strategy_override(client, mock_celery_task):
    """Strategy overrides should work alongside prompt lists."""

    response = client.post(
        "/api/workflows/article-proposal/run",
        json={
            "prompts": ["Research transformers"],
            "strategy": WorkflowStrategy.RESEARCH_PROPOSAL.value,
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == ["Research transformers"]
    assert workflow.strategy == WorkflowStrategy.RESEARCH_PROPOSAL


def test_workflow_run_prompts_in_repr(client, mock_celery_task):
    """The stored prompts should appear in the workflow representation."""

    response = client.post(
        "/api/workflows/article-proposal/run",
        json={
            "prompts": ["Test research prompt"],
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == ["Test research prompt"]

    repr_str = repr(workflow)
    assert "Test research prompt" in repr_str


def test_workflow_run_long_prompt_truncated_in_repr(client, mock_celery_task):
    """Long prompts should be truncated in the model representation."""

    long_prompt = "A" * 100
    response = client.post(
        "/api/workflows/article-proposal/run",
        json={
            "prompts": [long_prompt],
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == [long_prompt]
    assert len(workflow.prompt[0]) == 100

    repr_str = repr(workflow)
    assert "A" * 50 in repr_str
    assert "..." in repr_str


def test_workflow_run_async_propagates_prompts(client, mock_celery_task):
    """Async execution should queue workflows with the full prompt list."""

    payload = {
        "prompts": ["Async research prompt", "Follow up"],
        "async_execution": True,
    }

    response = client.post("/api/workflows/article-proposal/run", json=payload)

    assert response.status_code == 201

    # Verify Celery task was called with workflow_id
    mock_celery_task.delay.assert_called_once()
    workflow_id = mock_celery_task.delay.call_args[0][0]

    # Verify workflow has prompt stored
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    assert workflow.prompt == [prompt.strip() for prompt in payload["prompts"]]
