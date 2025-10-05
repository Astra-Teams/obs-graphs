"""Node that proposes new article themes based on extracted keywords."""

import json
import re
from pathlib import Path
from typing import Dict, List

from src.api.v1.prompts import render_prompt
from src.container import DependencyContainer
from src.protocols import NodeProtocol
from src.state import AgentResult


class GenerateThemesNode(NodeProtocol):
    """Ask the LLM to suggest new article themes."""

    def __init__(self, container: DependencyContainer):
        self._container = container

    def get_name(self) -> str:
        return "generate_themes"

    def validate_input(self, context: Dict) -> bool:
        keywords = context.get("keywords")
        return isinstance(keywords, list) and len(keywords) > 0

    def execute(self, vault_path: Path, context: Dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError("keywords are required before generating themes")

        keywords: List[str] = context["keywords"]
        existing_titles: List[str] = context.get("existing_titles", [])

        prompt = render_prompt(
            "generate_themes",
            keywords=keywords,
            existing_titles=existing_titles,
        )

        ollama_client = self._container.get_ollama_client()
        raw_response = ollama_client.generate(prompt)
        themes = self._parse_themes(raw_response)

        if not themes:
            return AgentResult(
                success=False,
                changes=[],
                message="Failed to parse LLM response for themes.",
                metadata={"state_updates": {"themes": [], "selected_theme": None}},
            )

        selected_theme = themes[0]
        metadata = {
            "state_updates": {
                "themes": themes,
                "selected_theme": selected_theme,
            }
        }

        message = f"Selected theme '{selected_theme}' from {len(themes)} suggestions."
        return AgentResult(success=True, changes=[], message=message, metadata=metadata)

    def _parse_themes(self, raw_response: str) -> List[str]:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{\s*\"themes\".*\}", raw_response, re.DOTALL)
            if not match:
                return []
            payload = json.loads(match.group(0))

        themes = payload.get("themes", [])
        if not isinstance(themes, list):
            return []
        return [str(theme).strip() for theme in themes if str(theme).strip()]
