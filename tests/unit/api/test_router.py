"""Unit tests for API router prompt validation."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.obs_graphs.api.router import router
from src.obs_graphs.db.database import Base, get_db
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
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task to prevent actual task execution."""
    with patch("src.obs_graphs.celery.tasks.run_workflow_task") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        mock_task.delay.return_value = mock_result
        yield mock_task


def test_workflow_run_with_valid_prompt(client, mock_celery_task):
    """Test that valid prompt is accepted and persisted to database."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "Research the impact of transformers on NLP",
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert "status" in data

    # Verify workflow was created in database with prompt
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow is not None
    assert workflow.prompt == "Research the impact of transformers on NLP"


def test_workflow_run_rejects_empty_prompt(client):
    """Test that an empty prompt is rejected."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "",
            "async_execution": True,
        },
    )

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("prompt" in str(error).lower() for error in error_detail)


def test_workflow_run_rejects_whitespace_only_prompt(client):
    """Test that whitespace-only prompt is rejected."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "   ",
            "async_execution": False,
        },
    )

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("prompt" in str(error).lower() for error in error_detail)


def test_workflow_run_rejects_missing_prompt(client):
    """Test that missing prompt field is rejected."""
    response = client.post(
        "/api/workflows/run",
        json={
            "async_execution": False,
        },
    )

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("prompt" in str(error).lower() for error in error_detail)


def test_workflow_run_prompt_strips_whitespace(client, mock_celery_task):
    """Test that prompt whitespace is stripped before storage."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "  Research topic with spaces  ",
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify prompt was stripped in database
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == "Research topic with spaces"


def test_workflow_run_with_strategy_override(client, mock_celery_task):
    """Test that prompt works with strategy override."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "Research transformers",
            "strategy": WorkflowStrategy.RESEARCH_PROPOSAL.value,
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify both prompt and strategy are stored
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == "Research transformers"
    assert workflow.strategy == WorkflowStrategy.RESEARCH_PROPOSAL


def test_workflow_run_prompt_in_metadata(client, mock_celery_task):
    """Test that prompt appears in workflow response metadata."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "Test research prompt",
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify prompt is accessible in workflow record
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == "Test research prompt"

    # Verify __repr__ includes prompt preview
    repr_str = repr(workflow)
    assert "Test research prompt" in repr_str


def test_workflow_run_long_prompt_truncated_in_repr(client, mock_celery_task):
    """Test that long prompts are truncated in __repr__ for readability."""
    long_prompt = "A" * 100  # 100 character prompt

    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": long_prompt,
            "async_execution": True,
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify full prompt is stored
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == data["id"]).first()
    assert workflow.prompt == long_prompt
    assert len(workflow.prompt) == 100

    # Verify __repr__ truncates to 50 chars + "..."
    repr_str = repr(workflow)
    assert "A" * 50 in repr_str
    assert "..." in repr_str


def test_workflow_run_async_propagates_prompt(client, mock_celery_task):
    """Test that async execution propagates prompt to Celery task."""
    response = client.post(
        "/api/workflows/run",
        json={
            "prompt": "Async research prompt",
            "async_execution": True,
        },
    )

    assert response.status_code == 201

    # Verify Celery task was called with workflow_id
    mock_celery_task.delay.assert_called_once()
    workflow_id = mock_celery_task.delay.call_args[0][0]

    # Verify workflow has prompt stored
    db = next(override_get_db())
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    assert workflow.prompt == "Async research prompt"
