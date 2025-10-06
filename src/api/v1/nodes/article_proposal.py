"""Agent for proposing new articles based on vault analysis."""

import json
from pathlib import Path

from langchain_community.llms import Ollama

from src.api.v1.prompts import render_prompt
from src.protocols import NodeProtocol
from src.settings import get_settings
from src.state import AgentResult


class ArticleProposalAgent(NodeProtocol):
    """
    Agent responsible for analyzing vault and proposing new articles.

    This agent analyzes the current vault structure and content to identify
    gaps or opportunities for new articles. It uses LLM to generate article
    proposals that will be passed to the content generation agent.
    """

    def __init__(self, llm: Ollama):
        """Initialize the article proposal agent."""
        self.llm = llm
        self._settings = get_settings()

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information.

        Args:
            context: Must contain 'prompt' for research topic generation

        Returns:
            True if context is valid, False otherwise
        """
        return (
            "prompt" in context
            and isinstance(context["prompt"], str)
            and len(context["prompt"].strip()) > 0
        )

    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        """
        Execute research topic proposal based on user prompt.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing 'prompt' with user's research request

        Returns:
            AgentResult with topic metadata (title, summary, tags, slug)

        Raises:
            ValueError: If input validation fails
        """
        if not self.validate_input(context):
            raise ValueError("Invalid context: prompt is required")

        prompt = context["prompt"].strip()

        # Generate research topic from prompt
        topic_prompt = render_prompt("research_topic_proposal", prompt=prompt)

        try:
            # Get LLM response with JSON topic proposal
            response = self.llm.invoke(topic_prompt)
            topic_data = self._parse_topic_proposal(response.content)

            if topic_data is None:
                return AgentResult(
                    success=False,
                    changes=[],
                    message="Failed to parse LLM response: malformed JSON",
                    metadata={"error": "malformed_json"},
                )

            # Store topic metadata for downstream nodes
            metadata = {
                "topic_title": topic_data["title"],
                "topic_summary": topic_data["summary"],
                "tags": topic_data["tags"],
                "proposal_slug": topic_data["slug"],
                "proposal_filename": f"{topic_data['slug']}.md",
            }

            message = f"Generated research topic: {topic_data['title']}"

            return AgentResult(
                success=True, changes=[], message=message, metadata=metadata
            )

        except Exception as e:
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to generate research topic: {str(e)}",
                metadata={"error": str(e)},
            )

    def _parse_topic_proposal(self, llm_response: str) -> dict | None:
        """
        Parse LLM response to extract topic proposal JSON.

        Args:
            llm_response: Raw response from LLM

        Returns:
            Dictionary with title, summary, tags, slug, or None if parsing fails
        """
        # Try to extract JSON from the response by finding the first '{' and last '}'
        start_index = llm_response.find("{")
        end_index = llm_response.rfind("}")
        if start_index != -1 and end_index > start_index:
            json_str = llm_response[start_index : end_index + 1]
            try:
                topic_data = json.loads(json_str)
                # Validate required fields
                required_fields = ["title", "summary", "tags", "slug"]
                if all(k in topic_data for k in required_fields):
                    # Validate tags format
                    if (
                        isinstance(topic_data["tags"], list)
                        and 3 <= len(topic_data["tags"]) <= 6
                    ):
                        # Ensure lowercase tags
                        topic_data["tags"] = [tag.lower() for tag in topic_data["tags"]]
                        return topic_data
            except json.JSONDecodeError:
                pass
        return None
