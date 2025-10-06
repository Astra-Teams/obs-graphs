"""HTTP client for ollama-deep-researcher service."""

import logging
from typing import Optional

import httpx

from src.protocols.research_client_protocol import ResearchResult

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

    def run_research(self, topic: str) -> ResearchResult:
        """
        Run research on the given topic.

        Args:
            topic: Research topic to investigate

        Returns:
            ResearchResult with summary and sources

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API response is invalid
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/research",
                    json={"topic": topic},
                )
                response.raise_for_status()

                data = response.json()
                return ResearchResult(
                    summary=data["summary"],
                    sources=data.get("sources", []),
                )

        except httpx.HTTPError as e:
            logger.error(f"Research API request failed: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid research API response: {e}")
            raise ValueError(f"Invalid API response format: {e}") from e
