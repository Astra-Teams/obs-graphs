"""Node that extracts representative keywords from a category."""

import json
import re
from pathlib import Path
from typing import Dict, List

from src.api.v1.prompts import render_prompt
from src.container import DependencyContainer
from src.protocols import NodeProtocol
from src.state import AgentResult


class ExtractKeywordsNode(NodeProtocol):
    """Use the LLM to extract keywords from all markdown files in a category."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def get_name(self) -> str:
        return "extract_keywords"

    def validate_input(self, context: Dict) -> bool:
        return isinstance(context.get("selected_category"), str)

    def execute(self, vault_path: Path, context: Dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError("selected_category is required before extracting keywords")

        category = context["selected_category"]
        vault_service = self._container.get_vault_service()
        category_content = vault_service.get_concatenated_content_from_category(
            category, vault_path
        )

        if not category_content.strip():
            return AgentResult(
                success=False,
                changes=[],
                message=f"No content found for category '{category}'.",
                metadata={
                    "state_updates": {
                        "category_content": "",
                        "keywords": [],
                        "existing_titles": [],
                    }
                },
            )

        prompt = render_prompt(
            "extract_keywords",
            category_name=category,
            category_content=category_content,
        )

        ollama_client = self._container.get_ollama_client()
        raw_response = ollama_client.generate(prompt)
        keywords = self._parse_keywords(raw_response)

        if not keywords:
            return AgentResult(
                success=False,
                changes=[],
                message="Failed to parse keywords from LLM response.",
                metadata={
                    "state_updates": {
                        "category_content": category_content,
                        "keywords": [],
                        "existing_titles": self._extract_titles(category_content),
                    }
                },
            )

        metadata = {
            "state_updates": {
                "category_content": category_content,
                "keywords": keywords,
                "existing_titles": self._extract_titles(category_content),
            }
        }

        message = f"Extracted {len(keywords)} keywords for category '{category}'."
        return AgentResult(success=True, changes=[], message=message, metadata=metadata)

    def _parse_keywords(self, raw_response: str) -> List[str]:
        """Parse a JSON payload containing a list of keywords."""
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{\s*\"keywords\".*\}", raw_response, re.DOTALL)
            if not match:
                return []
            payload = json.loads(match.group(0))

        keywords = payload.get("keywords", [])
        if not isinstance(keywords, list):
            return []
        return [str(keyword).strip() for keyword in keywords if str(keyword).strip()]

    def _extract_titles(self, content: str) -> List[str]:
        """Derive article titles from markdown headings."""
        titles: List[str] = []
        for line in content.splitlines():
            if line.startswith("#"):
                cleaned = line.lstrip("#").strip()
                if cleaned:
                    titles.append(cleaned)
        return titles
