"""LangGraph-based orchestration for the new article creation workflow."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from langgraph.graph import END, StateGraph

from src.api.v1.schemas import CreateNewArticleRequest
from src.container import DependencyContainer
from src.state import AgentResult, GraphState
from src.settings import get_settings


@dataclass
class NewArticleWorkflowResult:
    """Result of executing the new-article workflow."""

    success: bool
    pull_request_title: Optional[str] = None
    pull_request_body: Optional[str] = None
    pr_url: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


class GraphBuilder:
    """Construct and execute the simplified new-article workflow."""

    def __init__(self, container: Optional[DependencyContainer] = None):
        self._container = container or DependencyContainer()

    def create_new_article_workflow(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        workflow.add_node("select_category", self._create_node_runner("select_category"))
        workflow.add_node("extract_keywords", self._create_node_runner("extract_keywords"))
        workflow.add_node("generate_themes", self._create_node_runner("generate_themes"))
        workflow.add_node(
            "deep_search_placeholder",
            self._create_node_runner("deep_search_placeholder"),
        )
        workflow.add_node(
            "create_pull_request", self._create_node_runner("create_pull_request")
        )

        workflow.set_entry_point("select_category")
        workflow.add_edge("select_category", "extract_keywords")
        workflow.add_edge("extract_keywords", "generate_themes")
        workflow.add_edge("generate_themes", "deep_search_placeholder")
        workflow.add_edge("deep_search_placeholder", "create_pull_request")
        workflow.add_edge("create_pull_request", END)

        return workflow.compile()

    def run_new_article_workflow(
        self, request: CreateNewArticleRequest
    ) -> NewArticleWorkflowResult:
        settings = get_settings()
        vault_path = Path(request.vault_path or settings.WORKFLOW_CLONE_BASE_PATH)

        initial_state: GraphState = {
            "vault_path": vault_path,
            "requested_category": request.category,
            "available_categories": [],
            "selected_category": None,
            "category_content": "",
            "keywords": [],
            "existing_titles": [],
            "themes": [],
            "selected_theme": None,
            "report_markdown": "",
            "pull_request": {},
            "agent_results": {},
            "messages": [],
        }

        workflow = self.create_new_article_workflow()

        try:
            final_state = workflow.invoke(initial_state)
        except Exception as exc:  # pragma: no cover - defensive guard
            return NewArticleWorkflowResult(success=False, error=str(exc))

        pull_request = final_state.get("pull_request", {})
        metadata = {
            "selected_category": final_state.get("selected_category"),
            "keywords": final_state.get("keywords", []),
            "themes": final_state.get("themes", []),
            "messages": final_state.get("messages", []),
            "agent_results": final_state.get("agent_results", {}),
        }

        return NewArticleWorkflowResult(
            success=True,
            pull_request_title=pull_request.get("title"),
            pull_request_body=pull_request.get("body"),
            pr_url=pull_request.get("url"),
            metadata=metadata,
        )

    def _create_node_runner(self, node_name: str):
        def node_runner(state: GraphState) -> GraphState:
            node = self._container.get_node(node_name)
            context = dict(state)
            result: AgentResult = node.execute(state["vault_path"], context)

            updates = result.metadata.get("state_updates", {}) if result.metadata else {}
            if updates:
                state.update(updates)

            state.setdefault("agent_results", {})[node_name] = {
                "success": result.success,
                "message": result.message,
                "metadata": result.metadata,
            }
            state.setdefault("messages", []).append(result.message)

            return state

        return node_runner
