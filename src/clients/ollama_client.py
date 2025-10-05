"""Lightweight wrapper around the Ollama language model API."""

from __future__ import annotations

from typing import Any

from langchain_community.llms import Ollama as LangChainOllama


class OllamaClient:
    """Wrapper that exposes a simple ``generate`` method."""

    def __init__(self, model: str, base_url: str):
        self._client = LangChainOllama(model=model, base_url=base_url)

    @classmethod
    def from_llm(cls, llm: Any) -> "OllamaClient":
        """Create an ``OllamaClient`` from an arbitrary LangChain-compatible LLM."""
        instance = cls.__new__(cls)
        instance._client = llm
        return instance

    def generate(self, prompt: str) -> str:
        """Generate a completion for the provided prompt."""
        response = self._client.invoke(prompt)
        if isinstance(response, str):
            return response
        if hasattr(response, "content"):
            return getattr(response, "content")
        if hasattr(response, "text"):
            return getattr(response, "text")
        return str(response)
