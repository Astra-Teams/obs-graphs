"""Mock Ollama client for offline development and testing."""

from typing import Any, Iterator, List, Optional

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import BaseLLM
from langchain_core.outputs import GenerationChunk


class MockOllamaClient(BaseLLM):
    """
    Mock implementation of Ollama LLM client for offline development.

    This mock client returns fixed test JSON responses, allowing stable
    testing of LLM-dependent workflows without requiring an actual Ollama server.
    """

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return "mock_ollama"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Mock LLM call - returns fixed test JSON response.

        Args:
            prompt: Input prompt (logged but not used).
            stop: Stop sequences (ignored in mock).
            run_manager: Callback manager (ignored in mock).
            **kwargs: Additional arguments (ignored in mock).

        Returns:
            Fixed test JSON string.
        """
        print(f"[MockOllamaClient] _call() invoked with prompt length: {len(prompt)}")
        print("[MockOllamaClient] Returning mock LLM response")

        # Return a fixed test JSON response suitable for workflow testing
        return """{
  "status": "success",
  "message": "Mock LLM response for testing",
  "suggestions": [
    "Test suggestion 1",
    "Test suggestion 2",
    "Test suggestion 3"
  ],
  "confidence": 0.95
}"""

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        """
        Mock implementation of _generate method required by BaseLLM.

        Args:
            prompts: List of input prompts.
            stop: Stop sequences (ignored in mock).
            run_manager: Callback manager (ignored in mock).
            **kwargs: Additional arguments (ignored in mock).

        Returns:
            LLMResult with mock generation.
        """
        from langchain_core.outputs import Generation, LLMResult

        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
            generations.append([Generation(text=text)])

        return LLMResult(generations=generations)

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """
        Mock streaming implementation - yields response in one chunk.

        Args:
            prompt: Input prompt (logged but not used).
            stop: Stop sequences (ignored in mock).
            run_manager: Callback manager (ignored in mock).
            **kwargs: Additional arguments (ignored in mock).

        Yields:
            Single GenerationChunk with complete response.
        """
        text = self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
        yield GenerationChunk(text=text)
