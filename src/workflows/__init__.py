"""Workflow orchestration modules for agent execution."""

from src.graph.builder import (
    GraphBuilder,
    WorkflowPlan,
    WorkflowResult,
)

# Backward compatibility alias
WorkflowOrchestrator = GraphBuilder

__all__ = ["GraphBuilder", "WorkflowOrchestrator", "WorkflowPlan", "WorkflowResult"]
