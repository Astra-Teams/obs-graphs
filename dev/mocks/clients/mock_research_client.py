"""Mock research client for testing."""

from starprobe_sdk import ResearchResponse


class MockResearchApiClient:
    """Mock implementation of ResearchApiClient for testing."""

    def research(
        self, topic_title: str, backend: str | None = None
    ) -> ResearchResponse:
        """Mock research method that accepts backend parameter."""
        return ResearchResponse(
            success=True,
            article="# Mock Research Article\n\nThis is a mock response for testing.",
            metadata={
                "sources": [
                    "https://example.com/mock-source1",
                    "https://example.com/mock-source2",
                ],
                "source_count": 2,
            },
            diagnostics=["mock diagnostic"],
            processing_time=1.0,
            error_message=None,
        )
