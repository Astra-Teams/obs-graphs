"""Node for proposing new articles based on vault analysis."""

import json
from typing import Callable

from src.obs_graphs.graphs.article_proposal.prompts import render_prompt
from src.obs_graphs.graphs.article_proposal.state import NodeResult
from src.obs_graphs.protocols import NodeProtocol, StlConnClientProtocol


class ArticleProposalNode(NodeProtocol):
    """
    Node responsible for analyzing vault and proposing new articles.

    This node analyzes the current vault structure and content to identify
    gaps or opportunities for new articles. It uses LLM to generate article
    proposals that will be passed to the content generation node.
    """

    name = "article_proposal"

    def __init__(self, llm_provider: Callable[[str | None], StlConnClientProtocol]):
        """Initialize the article proposal node."""
        self._llm_provider = llm_provider

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information.

        Args:
            context: Must contain 'prompt' for research topic generation or 'vault_summary' for new article

        Returns:
            True if context is valid, False otherwise
        """
        strategy = context.get("strategy", "research_proposal")
        if strategy == "new_article":
            return "vault_summary" in context
        else:
            return (
                "prompts" in context
                and isinstance(context["prompts"], list)
                and len(context["prompts"]) > 0
                and len(context["prompts"][0].strip()) > 0
            )

    async def execute(self, context: dict) -> NodeResult:
        """
        Execute article proposal generation.

        Args:
            context: Dictionary containing vault_summary, strategy, and prompt

        Returns:
            NodeResult with article proposals or topic proposal
        """
        if not self.validate_input(context):
            raise ValueError("required fields missing")

        strategy = context.get("strategy", "new_article")
        # Backend parameter is ignored by stl-conn
        llm_client = self._llm_provider(None)

        if strategy == "research_proposal":
            return await self._execute_research_topic_proposal(context, llm_client)
        else:
            return await self._execute_new_article_proposal(context, llm_client)

    async def _execute_research_topic_proposal(
        self, context: dict, llm_client: StlConnClientProtocol
    ) -> NodeResult:
        """
        Execute research topic proposal based on user prompt.

        Args:
            context: Dictionary containing 'prompts' with user's research request (list of strings)

        Returns:
            NodeResult with topic metadata (title, summary, tags, slug)
        """
        # Use only the first prompt from the list for now
        prompt = context["prompts"][0].strip()

        # Check for intentional failure trigger
        if "fail intentionally" in prompt.lower():
            raise Exception("Intentional failure for testing purposes")

        # Generate research topic from prompt
        topic_prompt = render_prompt("research_topic_proposal", prompt=prompt)

        try:
            # Get LLM response with JSON topic proposal
            # StlConnClient.invoke() is async and returns LangChainResponse
            response = await llm_client.invoke(
                [{"role": "user", "content": topic_prompt}]
            )
            response_content = (
                response.content if hasattr(response, "content") else str(response)
            )
            topic_data = self._parse_topic_proposal(response_content)

            if topic_data is None:
                return NodeResult(
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

            return NodeResult(
                success=True, changes=[], message=message, metadata=metadata
            )

        except Exception as e:
            return NodeResult(
                success=False,
                changes=[],
                message=f"Failed to generate research topic: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_new_article_proposal(
        self, context: dict, llm_client: StlConnClientProtocol
    ) -> NodeResult:
        """
        Execute new article proposal based on vault analysis.

        Args:
            context: Dictionary containing 'vault_summary'

        Returns:
            NodeResult with article proposals
        """
        vault_summary = context["vault_summary"]

        # Generate new article proposals
        proposal_prompt = render_prompt(
            "new_article_creation",
            total_articles=vault_summary.total_articles,
        )

        try:
            # Get LLM response with JSON article proposals
            # StlConnClient.invoke() is async and returns LangChainResponse
            response = await llm_client.invoke(
                [{"role": "user", "content": proposal_prompt}]
            )
            response_content = (
                response.content if hasattr(response, "content") else str(response)
            )
            proposals = self._parse_article_proposals(response_content)

            if proposals is None:
                return NodeResult(
                    success=False,
                    changes=[],
                    message="Failed to parse LLM response: malformed JSON",
                    metadata={"error": "malformed_json"},
                )

            # Store article proposals for downstream nodes
            metadata = {
                "article_proposals": proposals,
            }

            message = f"Generated {len(proposals)} new article proposals"

            return NodeResult(
                success=True, changes=[], message=message, metadata=metadata
            )

        except Exception as e:
            return NodeResult(
                success=False,
                changes=[],
                message=f"Failed to generate article proposals: {str(e)}",
                metadata={"error": str(e)},
            )

    def _parse_article_proposals(self, llm_response: str) -> list | None:
        """
        Parse LLM response to extract article proposals JSON array.

        Args:
            llm_response: Raw response from LLM

        Returns:
            List of proposal dictionaries, or None if parsing fails
        """
        # Try to extract JSON from the response by finding the first '[' and last ']'
        start_index = llm_response.find("[")
        end_index = llm_response.rfind("]")
        if start_index != -1 and end_index > start_index:
            json_str = llm_response[start_index : end_index + 1]
            try:
                proposals = json.loads(json_str)
                if isinstance(proposals, list):
                    # Validate each proposal
                    for proposal in proposals:
                        required_fields = [
                            "title",
                            "category",
                            "description",
                            "filename",
                        ]
                        if not all(k in proposal for k in required_fields):
                            return None
                    return proposals
            except json.JSONDecodeError:
                pass
        return None

    def _parse_topic_proposal(self, llm_response: str) -> dict | None:
        """
        Parse LLM response to extract topic proposal JSON.

        Args:
            llm_response: Raw response from LLM

        Returns:
            Topic proposal dictionary, or None if parsing fails
        """
        # Try to extract JSON from the response by finding the first '{' and last '}'
        start_index = llm_response.find("{")
        end_index = llm_response.rfind("}")
        if start_index != -1 and end_index > start_index:
            json_str = llm_response[start_index : end_index + 1]
            try:
                topic_data = json.loads(json_str)
                if isinstance(topic_data, dict):
                    # Check if it's the expected format
                    required_fields = ["title", "summary", "tags", "slug"]
                    if all(k in topic_data for k in required_fields):
                        # Ensure tags is a list
                        if not isinstance(topic_data["tags"], list):
                            return None
                        return topic_data
            except json.JSONDecodeError:
                pass
        return None
