"""Mock research API client for testing."""

import logging

from src.protocols.research_client_protocol import ResearchResult

logger = logging.getLogger(__name__)


class MockResearchApiClient:
    """Mock research API client that returns deterministic responses."""

    def run_research(self, topic: str) -> ResearchResult:
        """
        Mock research execution.

        Args:
            topic: Research topic to investigate

        Returns:
            ResearchResult with mock summary and sources
        """
        logger.info(f"Mock research API: researching topic '{topic}'")

        # Return deterministic mock data
        return ResearchResult(
            summary=f"Mock research summary for topic: {topic}. "
            f"This is a comprehensive analysis covering key aspects, "
            f"findings, and recommendations based on available information.",
            sources=[
                "https://example.com/source1",
                "https://example.com/source2",
                "https://example.com/source3",
            ],
        )
