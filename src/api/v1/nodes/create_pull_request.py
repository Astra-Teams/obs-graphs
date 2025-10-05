"""Node responsible for creating a pull request with the generated report."""

import re
from pathlib import Path
from typing import Dict, List

from src.container import DependencyContainer
from src.protocols import NodeProtocol
from src.settings import get_settings
from src.state import AgentResult


class CreatePullRequestNode(NodeProtocol):
    """Create a GitHub pull request summarizing the generated report."""

    def __init__(self, container: DependencyContainer):
        self._container = container
        self._settings = get_settings()

    def get_name(self) -> str:
        return "create_pull_request"

    def validate_input(self, context: Dict) -> bool:
        return (
            isinstance(context.get("selected_theme"), str)
            and isinstance(context.get("report_markdown"), str)
        )

    def execute(self, vault_path: Path, context: Dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError(
                "selected_theme and report_markdown are required before creating a PR"
            )

        theme: str = context["selected_theme"]
        report_markdown: str = context.get("report_markdown", "")
        category: str | None = context.get("selected_category")
        keywords: List[str] = context.get("keywords", [])

        pr_title = theme
        pr_body = self._build_pull_request_body(theme, category, keywords, report_markdown)
        branch_name = f"new-article/{self._slugify(theme)}"

        github_client = self._container.get_github_client()
        try:
            pr = github_client.create_pull_request(
                repo_full_name=self._settings.OBSIDIAN_VAULT_REPO_FULL_NAME,
                head_branch=branch_name,
                title=pr_title,
                body=pr_body,
                base_branch=self._settings.WORKFLOW_DEFAULT_BRANCH,
            )
            pr_url = getattr(pr, "html_url", "")
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"Failed to create pull request: {exc}"
            return AgentResult(
                success=False,
                changes=[],
                message=message,
                metadata={
                    "state_updates": {
                        "pull_request": {
                            "title": pr_title,
                            "body": pr_body,
                            "url": "",
                        }
                    }
                },
            )

        metadata = {
            "state_updates": {
                "pull_request": {
                    "title": pr_title,
                    "body": pr_body,
                    "url": pr_url,
                }
            }
        }

        message = f"Created pull request for theme '{theme}'."
        return AgentResult(success=True, changes=[], message=message, metadata=metadata)

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "new-article"

    def _build_pull_request_body(
        self,
        theme: str,
        category: str | None,
        keywords: List[str],
        report_markdown: str,
    ) -> str:
        keyword_section = "\n".join(f"- {keyword}" for keyword in keywords) if keywords else "-"
        category_line = category or "未分類"
        sections = [
            f"## 提案テーマ\n\n- {theme}",
            f"\n## 対象カテゴリ\n\n- {category_line}",
            "\n## 主要キーワード\n\n" + keyword_section,
            "\n## リサーチメモ\n\n" + report_markdown,
        ]
        return "\n".join(sections)
