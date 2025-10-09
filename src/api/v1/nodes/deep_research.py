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
        Validate that the context contains required topic metadata.

        Args:
            context: Must contain topic_title, topic_summary, tags, and proposal_slug

        Returns:
            True if context is valid, False otherwise
        """
        required_fields = ["topic_title", "topic_summary", "tags", "proposal_slug"]
        return all(field in context for field in required_fields)

    def execute(self, context: dict) -> AgentResult:
        """
        Execute deep research and generate proposal document.
        """
        if not self.validate_input(context):
            raise ValueError(
                "Invalid context: topic metadata (title, summary, tags, slug) required"
            )

        topic_title = context["topic_title"]
        topic_summary = context["topic_summary"]
        tags = context["tags"]
        proposal_slug = context["proposal_slug"]

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
                tags=tags,
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
                "tags": tags,
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
        tags: list[str],
        research_summary: str,
        sources: list[str],
    ) -> str:
        """
        Generate Markdown proposal with YAML front matter.

        Args:
            title: Research topic title
            summary: Brief topic summary
            tags: List of tags
            research_summary: Research findings from API
            sources: List of source URLs

        Returns:
            Complete Markdown document string
        """
        # YAML front matter with tags only (as specified in requirements)
        yaml_tags = "\n".join(f"  - {tag}" for tag in tags)
        front_matter = f"---\ntags:\n{yaml_tags}\n---\n\n"

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
