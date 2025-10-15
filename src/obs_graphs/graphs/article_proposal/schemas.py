"""Pydantic models for article proposal graph schemas."""

from typing import TYPE_CHECKING, Annotated, Dict, List

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.obs_graphs.graphs.article_proposal.state import (
        FileChange,
        VaultSummary,
        WorkflowStrategy,
    )


class VaultSummaryModel(BaseModel):
    """Pydantic model for vault summary data."""

    total_articles: int
    categories: List[str]
    recent_updates: List[str]


class NodeResultModel(BaseModel):
    """Pydantic model for node execution results."""

    success: bool
    changes: List["FileChange"]
    message: str
    metadata: Dict = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)


class GraphStateModel(BaseModel):
    """Pydantic model for validating and serializing graph state."""

    vault_summary: "VaultSummary"
    strategy: str
    prompts: List[str]
    accumulated_changes: List["FileChange"]
    node_results: Dict
    messages: Annotated[List[str], "add_messages"]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
