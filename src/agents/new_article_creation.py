"""Agent for creating new articles from scratch in the Obsidian Vault."""

from pathlib import Path

from langchain_openai import ChatOpenAI

from src.agents.base import AgentResult, BaseAgent, FileAction, FileChange
from src.config.settings import get_settings


class NewArticleCreationAgent(BaseAgent):
    """
    Agent responsible for creating new articles from scratch.

    This agent analyzes the current vault structure and content to identify
    gaps or opportunities for new articles. It uses LLM to generate high-quality
    article content based on vault analysis.
    """

    def __init__(self):
        """Initialize the new article creation agent."""
        settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY,
        )

    def get_name(self) -> str:
        """Get the name of this agent."""
        return "NewArticleCreationAgent"

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
        Execute new article creation based on vault analysis.

        Args:
            vault_path: Path to the local clone of the Obsidian Vault
            context: Dictionary containing vault_summary with categories and existing articles

        Returns:
            AgentResult with new file changes to create articles

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

            # Generate content for each suggested article
            changes = []
            for suggestion in article_suggestions:
                article_content = self._generate_article_content(
                    suggestion, vault_summary
                )
                changes.append(
                    FileChange(
                        path=suggestion["path"],
                        action=FileAction.CREATE,
                        content=article_content,
                    )
                )

            metadata = {
                "articles_created": len(changes),
                "vault_articles_count": total_articles,
                "categories_analyzed": len(categories),
            }

            message = f"Created {len(changes)} new article(s) based on vault analysis"

            return AgentResult(
                success=True, changes=changes, message=message, metadata=metadata
            )

        except Exception as e:
            return AgentResult(
                success=False,
                changes=[],
                message=f"Failed to create new articles: {str(e)}",
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
        categories = vault_summary.get("categories", [])
        total_articles = vault_summary.get("total_articles", 0)
        recent_updates = vault_summary.get("recent_updates", [])

        prompt = f"""Analyze this Obsidian Vault and suggest new articles to create.

Vault Summary:
- Total articles: {total_articles}
- Categories: {', '.join(categories) if categories else 'None'}
- Recent updates: {', '.join(recent_updates[:5]) if recent_updates else 'None'}

Based on this analysis, suggest 1-3 new articles that would add value to this vault.
Consider:
1. Gaps in coverage across categories
2. Topics that would connect well with existing content
3. Foundational concepts that may be missing

For each suggested article, provide:
1. Title (clear and concise)
2. Category (existing or new)
3. Brief description of content focus
4. Filename (in format: category/article-title.md)

Format your response as a JSON array:
[
  {{
    "title": "Article Title",
    "category": "Category Name",
    "description": "What this article should cover",
    "filename": "category/article-title.md"
  }}
]
"""
        return prompt

    def _parse_article_suggestions(self, llm_response: str) -> list[dict]:
        """
        Parse LLM response to extract article suggestions.

        Args:
            llm_response: Raw response from LLM

        Returns:
            List of article suggestion dictionaries
        """
        import json
        import re

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
                return valid_suggestions[:3]  # Limit to 3 articles max
            except json.JSONDecodeError:
                pass

        # Fallback: return empty list if parsing fails
        return []

    def _generate_article_content(
        self, suggestion: dict, vault_summary: dict
    ) -> str:
        """
        Generate full article content based on suggestion.

        Args:
            suggestion: Article suggestion dictionary
            vault_summary: Vault summary for context

        Returns:
            Complete markdown content for the article
        """
        content_prompt = f"""Create a comprehensive Obsidian markdown article with the following specifications:

Title: {suggestion['title']}
Category: {suggestion['category']}
Description: {suggestion['description']}

The article should:
1. Start with a frontmatter section (YAML) including title, category, and creation date
2. Have a clear introduction explaining the topic
3. Include well-structured sections with headers
4. Be informative and well-researched
5. Use markdown formatting appropriately (headers, lists, code blocks, etc.)
6. Leave placeholders for links to related articles (we'll add these later)
7. Be between 300-800 words

Format as a complete markdown file ready to save.
"""

        try:
            response = self.llm.invoke(content_prompt)
            content = response.content

            # Ensure frontmatter is present
            if not content.startswith("---"):
                # Add minimal frontmatter
                import datetime

                frontmatter = f"""---
title: {suggestion['title']}
category: {suggestion['category']}
created: {datetime.datetime.now().strftime('%Y-%m-%d')}
---

"""
                content = frontmatter + content

            return content

        except Exception:
            # Fallback to minimal article structure
            import datetime

            return f"""---
title: {suggestion['title']}
category: {suggestion['category']}
created: {datetime.datetime.now().strftime('%Y-%m-%d')}
---

# {suggestion['title']}

{suggestion['description']}

## Overview

[Content to be expanded]

## Related Topics

- [Links to be added]
"""
