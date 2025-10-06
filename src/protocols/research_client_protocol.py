"""Protocol for research API client."""

from typing import List, Protocol

from pydantic import BaseModel


class ResearchResult(BaseModel):
    """Result from research API."""

    summary: str
    sources: List[str]


class ResearchClientProtocol(Protocol):
    """Protocol for research API client."""

    def run_research(self, topic: str) -> ResearchResult:
        """
        Run research on the given topic.

        Args:
            topic: Research topic to investigate

        Returns:
            ResearchResult with summary and sources
        """
        ...
