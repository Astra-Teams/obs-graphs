"""Agent for proposing new articles based on vault analysis."""

import json
import re
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
            context: Must contain 'vault_summary' with vault analysis data

        Returns:
            True if context is valid, False otherwise
        """
        if "vault_summary" not in context:
            return False
        vault_summary = context["vault_summary"]
        return isinstance(vault_summary, dict) and "categories" in vault_summary

    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        """
        Execute article proposal based on vault analysis.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing vault_summary with categories and existing articles

        Returns:
            AgentResult with article_proposals in metadata

        Raises:
            ValueError: If input validation fails
        """
        if not self.validate_input(context):
            raise ValueError(
                "Invalid context: vault_summary with categories is required"
            )

        vault_summary = context["vault_summary"]
        categories = vault_summary.get("categories", [])
        total_articles = vault_summary.get("total_articles", 0)

        # Analyze vault to identify new article opportunities
        analysis_prompt = self._create_analysis_prompt(vault_summary)

        try:
            # Get LLM suggestions for new articles
            response = self.llm.invoke(analysis_prompt)
            article_suggestions = self._parse_article_suggestions(response.content)

            # Check if parsing failed (malformed response)
            if article_suggestions is None:
                return AgentResult(
                    success=False,
                    changes=[],
                    message="Failed to parse LLM response: malformed JSON",
                    metadata={"error": "malformed_json"},
                )

            # Check if no articles were suggested
            if len(article_suggestions) == 0:
                return AgentResult(
                    success=True,
                    changes=[],
                    message="No new articles needed based on vault analysis",
                    metadata={
                        "article_proposals": [],
                        "vault_articles_count": total_articles,
                        "categories_analyzed": len(categories),
                    },
                )

            metadata = {
                "article_proposals": article_suggestions,
                "proposals_count": len(article_suggestions),
                "vault_articles_count": total_articles,
                "categories_analyzed": len(categories),
            }

            message = f"Proposed {len(article_suggestions)} new article(s) based on vault analysis"

            return AgentResult(
                success=True, changes=[], message=message, metadata=metadata
            )

        except Exception as e:
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to propose new articles: {str(e)}",
                metadata={"error": str(e)},
            )

    def _create_analysis_prompt(self, vault_summary: dict) -> str:
        """
        Create a prompt for analyzing the vault and suggesting new articles.

        Args:
            vault_summary: Summary of the vault's current state

        Returns:
            Prompt string for LLM
        """
        return render_prompt(
            "new_article_creation",
            total_articles=vault_summary.get("total_articles", 0),
            categories=vault_summary.get("categories", []),
            recent_updates=vault_summary.get("recent_updates", []),
        )

    def _parse_article_suggestions(self, llm_response: str) -> list[dict] | None:
        """
        Parse LLM response to extract article suggestions.

        Args:
            llm_response: Raw response from LLM

        Returns:
            List of article suggestion dictionaries, or None if parsing fails
        """
        # Try to extract JSON from the response
        json_match = re.search(r"\[.*\]", llm_response, re.DOTALL)
        if json_match:
            try:
                suggestions = json.loads(json_match.group())
                # Validate and normalize suggestions
                valid_suggestions = []
                for s in suggestions:
                    if all(k in s for k in ["title", "category", "filename"]):
                        valid_suggestions.append(
                            {
                                "title": s["title"],
                                "category": s["category"],
                                "description": s.get("description", ""),
                                "path": s["filename"],
                            }
                        )
                return valid_suggestions[
                    : self._settings.MAX_NEW_ARTICLES_PER_RUN
                ]  # Limit to max articles per run
            except json.JSONDecodeError:
                return None

        # Fallback: return None if parsing fails
        return None
