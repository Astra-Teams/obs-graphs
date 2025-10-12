"""LLM client implementation backed by an Ollama server."""

from __future__ import annotations

import logging
from typing import Optional, Type, TypeVar

from langchain_community.llms import Ollama as LangchainOllama
from langchain_core.language_models.llms import BaseLLM
from pydantic import BaseModel

from src.obs_graphs.clients._llm_utils import parse_structured_response
from src.obs_graphs.protocols.llm_client_protocol import LLMClientProtocol

logger = logging.getLogger(__name__)

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class OllamaClient(LLMClientProtocol):
    """Adapter around LangChain's Ollama LLM implementation."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str],
        *,
        llm: Optional[BaseLLM] = None,
    ) -> None:
        """
        Initialize the client.

        Args:
            model: Ollama model identifier.
            base_url: Base URL for the Ollama REST API.
            llm: Optional pre-configured LangChain LLM instance (useful for tests).
        """
        if llm is not None:
            self._llm = llm
        else:
            kwargs = {"model": model}
            if base_url:
                kwargs["base_url"] = base_url
            self._llm = LangchainOllama(**kwargs)

    def invoke(self, prompt: str) -> str:
        """Execute the prompt and return the raw text."""
        logger.debug("Invoking Ollama model with prompt length %s", len(prompt))
        return self._llm.invoke(prompt)

    def invoke_as_structured_output(
        self,
        prompt: str,
        schema: Type[StructuredModelT],
    ) -> StructuredModelT:
        """
        Execute the prompt and parse the response into the provided schema.

        Raises:
            ValueError: If the response cannot be parsed into the schema.
        """
        raw_response = self.invoke(prompt)
        try:
            payload = parse_structured_response(raw_response)
            return schema.model_validate(payload)
        except ValueError as exc:
            logger.warning("Failed to parse Ollama response as JSON: %s", exc)
            raise
