"""Enums used across the application."""

from enum import Enum


class WorkflowStrategy(str, Enum):
    """Enumeration of available workflow strategies."""

    RESEARCH_PROPOSAL = "research_proposal"
