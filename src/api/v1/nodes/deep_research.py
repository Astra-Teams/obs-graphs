"""Agent for conducting deep research using ollama-deep-researcher service."""

import logging
from datetime import datetime

from src.protocols import NodeProtocol, ResearchClientProtocol
from src.state import AgentResult, FileAction, FileChange

logger = logging.getLogger(__name__)


class DeepResearchAgent(NodeProtocol):
    """
    Agent responsible for conducting deep research and generating proposal documents.

    This agent takes topic metadata from the article_proposal node, calls the
    research API to gather findings, and generates a Markdown proposal file
    with YAML front matter.
    """

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
        Execute deep research and generate proposal document.
        """
        if not self.validate_input(context):
            raise ValueError("Invalid context: topic_title is required")

        topic_title = context["topic_title"]
        topic_summary = context.get("topic_summary", f"Research on {topic_title}")
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

            # Generate Markdown content with YAML front matter
            markdown_content = self._generate_proposal_markdown(
                title=topic_title,
                summary=topic_summary,
                research_summary=research_result.summary,
                sources=research_result.sources,
            )

            # Create file change
            file_change = FileChange(
                path=file_path,
                action=FileAction.CREATE,
                content=markdown_content,
            )

            metadata = {
                "proposal_filename": filename,
                "proposal_path": file_path,
                "sources_count": len(research_result.sources),
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

    def _generate_proposal_markdown(
        self,
        title: str,
        summary: str,
        research_summary: str,
        sources: list[str],
    ) -> str:
        """
        Generate Markdown proposal with YAML front matter.

        Args:
            title: Research topic title
            summary: Brief topic summary
            research_summary: Research findings from API
            sources: List of source URLs

        Returns:
            Complete Markdown document string
        """
        # No YAML front matter needed
        front_matter = ""

        # Markdown body
        body = f"# {title}\n\n"
        body += f"## Summary\n\n{summary}\n\n"
        body += f"## Research Findings\n\n{research_summary}\n\n"

        # Sources section
        if sources:
            body += "## Sources\n\n"
            for i, source in enumerate(sources, 1):
                body += f"{i}. {source}\n"

        return front_matter + body
