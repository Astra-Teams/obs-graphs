"""Protocol for research API client."""

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field


class ResearchResult(BaseModel):
    """Result from research API."""

    article: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: List[str] = Field(default_factory=list)
    processing_time: Optional[float] = None


class ResearchClientProtocol(Protocol):
    """Protocol for research API client."""

    def run_research(
        self,
        query: str,
        backend: Optional[str] = None,
    ) -> ResearchResult:
        """
        Run research on the given query.

        Args:
            query: Search query to investigate
            backend: Optional identifier for the LLM backend to use

        Returns:
            ResearchResult containing the generated article and metadata
        """
        ...
