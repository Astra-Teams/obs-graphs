"""Node for conducting deep research using ollama-deep-researcher service."""

import logging
from datetime import datetime

from olm_d_rch_sdk import ResearchClientProtocol, ResearchResponse

from src.obs_graphs.graphs.article_proposal.state import (
    FileAction,
    FileChange,
    NodeResult,
)
from src.obs_graphs.protocols import NodeProtocol

logger = logging.getLogger(__name__)


class DeepResearchNode(NodeProtocol):
    """
    Node responsible for delegating deep research and persisting returned articles.

    This node takes topic metadata from the article_proposal node, calls the
    research API to gather findings, and writes the generated Markdown article
    directly to disk without additional formatting.
    """

    name = "deep_research"

    def __init__(self, research_client: ResearchClientProtocol):
        """Initialize the deep research node."""
        self.research_client = research_client

    def validate_input(self, state: dict) -> bool:
        """
        Validate that the context contains at least the topic title.

        Args:
            context: Must contain at least topic_title

        Returns:
            True if context has minimum required data, False otherwise
        """
        # Only require topic_title as minimum, others can be generated/defaulted
        return (
            "topic_title" in state
            and isinstance(state["topic_title"], str)
            and len(state["topic_title"].strip()) > 0
        )

    async def execute(self, state: dict) -> NodeResult:
        """
        Execute deep research and persist the returned article.
        """
        if not self.validate_input(state):
            raise ValueError("Invalid context: topic_title is required")

        topic_title = state["topic_title"]
        proposal_slug = state.get(
            "proposal_slug",
            topic_title.lower()
            .replace(" ", "-")
            .replace(",", "")
            .replace(".", "")[:50],
        )

        try:
            # Call research API with topic
            logger.info(f"Starting research for topic: {topic_title}")
            research_result: ResearchResponse = self.research_client.research(
                topic_title
            )

            if not research_result.success:
                error_message = (
                    research_result.error_message or "Research API reported failure"
                )
                raise ValueError(error_message)

            article_content = (research_result.article or "").strip()
            if not article_content:
                raise ValueError("Research API response missing article content")

            metadata = research_result.metadata or {}
            if not isinstance(metadata, dict):
                metadata = {}

            diagnostics = list(research_result.diagnostics or [])

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{proposal_slug}-{timestamp}.md"
            file_path = f"proposals/{filename}"

            # Create file change
            file_change = FileChange(
                path=file_path,
                action=FileAction.CREATE,
                content=article_content,
            )

            metadata = {
                "proposal_filename": filename,
                "proposal_path": file_path,
                "sources_count": metadata.get("source_count", 0),
                "research_metadata": metadata,
                "diagnostics": diagnostics,
                "processing_time_seconds": research_result.processing_time,
            }

            message = f"Generated research proposal: {filename}"

            return NodeResult(
                success=True,
                changes=[file_change],
                message=message,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            return NodeResult(
                success=False,
                changes=[],
                message=f"Failed to conduct research: {str(e)}",
                metadata={"error": str(e)},
            )
