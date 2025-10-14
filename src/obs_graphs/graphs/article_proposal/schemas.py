"""Pydantic models for article proposal graph schemas."""

from typing import TYPE_CHECKING, Dict, List

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.obs_graphs.graphs.article_proposal.state import (
        FileChange,
        WorkflowStrategy,
    )


class VaultSummaryModel(BaseModel):
    """Pydantic model for vault summary data."""

    total_articles: int
    categories: List[str]
    recent_updates: List[str]


class AgentResultModel(BaseModel):
    """Pydantic model for agent execution results."""

    success: bool
    changes: List["FileChange"]
    message: str
    metadata: Dict = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)


class GraphStateModel(BaseModel):
    """Pydantic model for validating and serializing graph state."""

    vault_summary: VaultSummaryModel
    strategy: "WorkflowStrategy"
    prompt: List[str]
    accumulated_changes: List["FileChange"]
    node_results: Dict[str, AgentResultModel]
    messages: List[str]

    model_config = ConfigDict(arbitrary_types_allowed=True)
