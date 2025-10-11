"""Agent for conducting deep research using ollama-deep-researcher service."""

import logging
from datetime import datetime

from src.obs_graphs.graphs.article_proposal.state import (
    AgentResult,
    FileAction,
    FileChange,
)
from src.obs_graphs.protocols import NodeProtocol, ResearchClientProtocol

logger = logging.getLogger(__name__)


class DeepResearchAgent(NodeProtocol):
    """
    Agent responsible for delegating deep research and persisting returned articles.

    This agent takes topic metadata from the article_proposal node, calls the
    research API to gather findings, and writes the generated Markdown article
    directly to disk without additional formatting.
    """

    name = "deep_research"

    def __init__(self, research_client: ResearchClientProtocol):
        """Initialize the deep research agent."""
        self.research_client = research_client

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains at least the topic title.

        Args:
            context: Must contain at least topic_title

        Returns:
            True if context has minimum required data, False otherwise
        """
        # Only require topic_title as minimum, others can be generated/defaulted
        return (
            "topic_title" in context
            and isinstance(context["topic_title"], str)
            and len(context["topic_title"].strip()) > 0
        )

    def execute(self, context: dict) -> AgentResult:
        """
        Execute deep research and persist the returned article.
        """
        if not self.validate_input(context):
            raise ValueError("Invalid context: topic_title is required")

        topic_title = context["topic_title"]
        proposal_slug = context.get(
            "proposal_slug",
            topic_title.lower()
            .replace(" ", "-")
            .replace(",", "")
            .replace(".", "")[:50],
        )

        try:
            # Call research API with topic
            logger.info(f"Starting research for topic: {topic_title}")
            research_result = self.research_client.run_research(topic_title)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{proposal_slug}-{timestamp}.md"
            file_path = f"proposals/{filename}"

            # Create file change
            file_change = FileChange(
                path=file_path,
                action=FileAction.CREATE,
                content=research_result.article,
            )

            metadata = {
                "proposal_filename": filename,
                "proposal_path": file_path,
                "sources_count": research_result.metadata.get("source_count", 0),
                "research_metadata": research_result.metadata,
                "diagnostics": research_result.diagnostics,
                "processing_time_seconds": research_result.processing_time,
                "topic_summary": context.get("topic_summary"),
            }

            message = f"Generated research proposal: {filename}"

            return AgentResult(
                success=True,
                changes=[file_change],
                message=message,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to conduct research: {str(e)}",
                metadata={"error": str(e)},
            )
