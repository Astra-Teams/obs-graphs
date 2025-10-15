"""Pydantic models used by the obs-graphs workflow SDK."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class WorkflowRequest(BaseModel):
    """Payload for executing a workflow via the obs-graphs API."""

    prompts: List[str] = Field(
        ...,
        description=(
            "Ordered prompts that guide the workflow. The first entry is treated "
            "as the primary instruction."
        ),
        min_length=1,
    )
    strategy: Optional[str] = Field(
        None,
        description="Optional workflow strategy to force a particular execution path.",
    )
    async_execution: bool = Field(
        False,
        description="Queue the workflow for asynchronous processing via Celery.",
    )

    @field_validator("prompts", mode="after")
    @classmethod
    def _validate_prompts(cls, prompts: List[str]) -> List[str]:
        cleaned: List[str] = []
        for index, prompt in enumerate(prompts):
            stripped = prompt.strip()
            if not stripped:
                raise ValueError(
                    f"Prompts cannot contain empty values; index {index} is empty."
                )
            cleaned.append(stripped)
        return cleaned


class WorkflowResponse(BaseModel):
    """Response returned by the workflow execution endpoint."""

    id: int = Field(..., description="Identifier of the workflow run.")
    status: str = Field(
        ..., description="Status of the workflow (e.g. PENDING, RUNNING, COMPLETED)."
    )
    message: str = Field(..., description="Summary message from the workflow run.")
    celery_task_id: Optional[str] = Field(
        None, description="Celery task identifier when async execution is requested."
    )
