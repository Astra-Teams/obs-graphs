"""Agent for generating article content from proposals."""

import datetime
from pathlib import Path

from langchain_community.llms import Ollama

from src.api.prompts import render_prompt
from src.protocols import NodeProtocol
from src.settings import get_settings
from src.state import AgentResult, FileAction, FileChange


class ArticleContentGenerationAgent(NodeProtocol):
    """
    Agent responsible for generating article content from proposals.

    This agent takes article proposals (from ArticleProposalAgent) and generates
    full markdown content for each proposed article using LLM.
    """

    def __init__(self, llm: Ollama):
        """Initialize the article content generation agent."""
        self.llm = llm
        self._settings = get_settings()

    def validate_input(self, context: dict) -> bool:
        """
        Validate that the context contains required information.

        Args:
            context: Must contain 'article_proposals' with proposal data

        Returns:
            True if context is valid, False otherwise
        """
        if "article_proposals" not in context:
            return False
        proposals = context["article_proposals"]
        return isinstance(proposals, list)

    def execute(self, context: dict) -> AgentResult:
        """
        Execute article content generation based on proposals.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing article_proposals from ArticleProposalAgent

        Returns:
            AgentResult with new file changes to create articles

        Raises:
            ValueError: If input validation fails
        """
        if not self.validate_input(context):
            raise ValueError("Invalid context: article_proposals list is required")

        article_proposals = context["article_proposals"]
        vault_summary = context.get("vault_summary", {})  # noqa: F841

        # Generate timestamp once for consistency
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

        # If no proposals, return success with no changes
        if len(article_proposals) == 0:
            return AgentResult(
                success=True,
                changes=[],
                message="No articles to generate",
                metadata={"articles_created": 0},
            )

        try:
            # Generate content for each proposed article
            changes = []
            for proposal in article_proposals:
                article_content = self._generate_article_content(proposal, timestamp)
                target_path = Path("drafts/obs-graphs/create-new-article") / proposal[
                    "filename"
                ].lstrip("/")
                changes.append(
                    FileChange(
                        path=str(target_path.as_posix()),
                        action=FileAction.CREATE,
                        content=article_content,
                    )
                )

            metadata = {
                "articles_created": len(changes),
            }

            message = f"Created {len(changes)} new article(s) from proposals"

            return AgentResult(
                success=True, changes=changes, message=message, metadata=metadata
            )

        except Exception as e:
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to generate article content: {str(e)}",
                metadata={"error": str(e)},
            )

    def _generate_article_content(self, proposal: dict, timestamp: str) -> str:
        """
        Generate full article content based on proposal.

        Args:
            proposal: Article proposal dictionary
            timestamp: Creation timestamp for consistency

        Returns:
            Complete markdown content for the article
        """
        content_prompt = render_prompt(
            "new_article_content",
            title=proposal["title"],
            category=proposal["category"],
            description=proposal["description"],
        )

        try:
            response = self.llm.invoke(content_prompt)
            content = response.content

            # Ensure frontmatter is present
            if not content.startswith("---"):
                # Add minimal frontmatter
                frontmatter = f"""---
title: {proposal['title']}
category: {proposal['category']}
created: {timestamp}
---

"""
                content = frontmatter + content

            return content

        except Exception:
            # Fallback to minimal article structure on LLM errors
            return f"""---
title: {proposal['title']}
category: {proposal['category']}
created: {timestamp}
---

# {proposal['title']}

{proposal['description']}

## Overview

[Content to be expanded]

## Related Topics

- [Links to be added]
"""
