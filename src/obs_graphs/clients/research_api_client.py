"""HTTP client for ollama-deep-researcher service."""

import logging
from typing import Optional

import httpx

from src.obs_graphs.protocols.research_client_protocol import ResearchResult

logger = logging.getLogger(__name__)


class ResearchApiClient:
    """Client for communicating with ollama-deep-researcher service."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
    ):
        """
        Initialize research API client.

        Args:
            base_url: Base URL of the research API service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def run_research(self, query: str, backend: Optional[str] = None) -> ResearchResult:
        """
        Run research on the given query.

        Args:
            query: Search query or topic description
            backend: Optional identifier for the LLM backend to use

        Returns:
            ResearchResult containing generated article and metadata

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API response is invalid
        """
        try:
            endpoint = self.base_url
            if not endpoint.endswith("/research"):
                endpoint = f"{endpoint}/research"

            payload = {"query": query}
            if backend:
                payload["backend"] = backend

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()

                data = response.json()
                if not data.get("success", False):
                    error_message = data.get("error_message") or "Unknown error"
                    raise ValueError(f"Research API reported failure: {error_message}")

                article = data.get("article")
                if not isinstance(article, str) or not article.strip():
                    raise ValueError("Research API response missing article content")

                metadata = data.get("metadata") or {}
                if not isinstance(metadata, dict):
                    raise ValueError("Research API metadata must be a JSON object")

                diagnostics = data.get("diagnostics") or []
                if not isinstance(diagnostics, list):
                    raise ValueError("Research API diagnostics must be a list")

                processing_time = data.get("processing_time")
                if processing_time is not None:
                    try:
                        processing_time = float(processing_time)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            "Research API processing_time must be numeric"
                        ) from exc

                return ResearchResult(
                    article=article,
                    metadata=metadata,
                    diagnostics=[str(item) for item in diagnostics],
                    processing_time=processing_time,
                )

        except httpx.HTTPError as e:
            logger.error(f"Research API request failed: {e}")
            raise
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid research API response: {e}")
            raise ValueError(f"Invalid API response format: {e}") from e
