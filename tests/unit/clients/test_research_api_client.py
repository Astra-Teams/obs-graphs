"""Unit tests for ResearchApiClient."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.clients.research_api_client import ResearchApiClient
from src.protocols.research_client_protocol import ResearchResult


@pytest.fixture
def client():
    """Create ResearchApiClient instance."""
    return ResearchApiClient(base_url="http://test-api:8000", timeout=30.0)


def test_client_initialization():
    """Test that client initializes with correct settings."""
    client = ResearchApiClient(base_url="http://test-api:8000", timeout=60.0)
    assert client.base_url == "http://test-api:8000"
    assert client.timeout == 60.0


def test_client_strips_trailing_slash():
    """Test that base_url trailing slash is removed."""
    client = ResearchApiClient(base_url="http://test-api:8000/", timeout=30.0)
    assert client.base_url == "http://test-api:8000"


def test_client_default_timeout():
    """Test that client uses default timeout when not specified."""
    client = ResearchApiClient(base_url="http://test-api:8000")
    assert client.timeout == 300.0


@patch("httpx.Client")
def test_run_research_success(mock_client_class, client):
    """Test successful research API call."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "summary": "Research findings on transformers",
        "sources": [
            "https://arxiv.org/abs/1706.03762",
            "https://example.com/nlp",
        ],
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client_class.return_value = mock_client

    # Execute
    result = client.run_research("Transformers in NLP")

    # Verify
    assert isinstance(result, ResearchResult)
    assert result.summary == "Research findings on transformers"
    assert len(result.sources) == 2
    assert result.sources[0] == "https://arxiv.org/abs/1706.03762"

    # Verify API call
    mock_client.post.assert_called_once_with(
        "http://test-api:8000/research",
        json={"topic": "Transformers in NLP"},
    )


@patch("httpx.Client")
def test_run_research_without_sources(mock_client_class, client):
    """Test research API call when sources field is missing."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "summary": "Research findings",
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client_class.return_value = mock_client

    # Execute
    result = client.run_research("Test topic")

    # Verify - sources should default to empty list
    assert isinstance(result, ResearchResult)
    assert result.summary == "Research findings"
    assert result.sources == []


@patch("httpx.Client")
def test_run_research_http_error(mock_client_class, client):
    """Test that HTTP errors are properly raised."""
    # Setup mock to raise HTTPError
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.HTTPError("Connection failed")
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client_class.return_value = mock_client

    # Execute and verify error
    with pytest.raises(httpx.HTTPError, match="Connection failed"):
        client.run_research("Test topic")


@patch("httpx.Client")
def test_run_research_invalid_response_format(mock_client_class, client):
    """Test that invalid API response format raises ValueError."""
    # Setup mock with missing required field
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "invalid_field": "value",
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client_class.return_value = mock_client

    # Execute and verify error
    with pytest.raises(ValueError, match="Invalid API response format"):
        client.run_research("Test topic")


@patch("httpx.Client")
def test_run_research_timeout_setting(mock_client_class, client):
    """Test that timeout is passed to httpx Client."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "summary": "Test",
        "sources": [],
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client_class.return_value = mock_client

    # Execute
    client.run_research("Test topic")

    # Verify timeout was passed to Client constructor
    mock_client_class.assert_called_once_with(timeout=30.0)
