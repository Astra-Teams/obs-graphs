"""Protocol for LLM clients used by obs-graphs."""

from __future__ import annotations

from typing import Protocol, Type, TypeVar

from pydantic import BaseModel

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class LLMClientProtocol(Protocol):
    """Protocol defining the expected interface for LLM clients."""

    def invoke(self, prompt: str) -> str:
        """Execute the prompt and return the raw string response."""
        ...

    def invoke_as_structured_output(
        self,
        prompt: str,
        schema: Type[StructuredModelT],
    ) -> StructuredModelT:
        """
        Execute the prompt and parse the response into the given schema.

        Implementations should raise ValueError if the response cannot be
        parsed into the requested schema.
        """
        ...
