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
        Mock LLM call - returns context-aware test JSON response.

        Args:
            prompt: Input prompt (used to determine response type).
            stop: Stop sequences (ignored in mock).
            run_manager: Callback manager (ignored in mock).
            **kwargs: Additional arguments (ignored in mock).

        Returns:
            Context-appropriate test JSON string.
        """
        print(f"[MockOllamaClient] _call() invoked with prompt length: {len(prompt)}")
        print(f"[MockOllamaClient] Prompt preview: {prompt[:200]}...")
        print("[MockOllamaClient] Returning mock LLM response")

        # Detect prompt type and return appropriate JSON
        if "fail" in prompt.lower():
            print("[MockOllamaClient] Detected: intentional failure")
            raise Exception("Mock LLM failure for testing")
        elif "research topic" in prompt.lower() or "topic proposal" in prompt.lower():
            print("[MockOllamaClient] Detected: research topic proposal")
            # Return topic metadata for article_proposal node
            return """{
  "title": "Test Article Title",
  "summary": "This is a test article summary for E2E testing purposes.",
  "tags": ["testing", "e2e", "mock"],
  "slug": "test-article-title"
}"""
        elif "suggest new articles" in prompt.lower():
            print("[MockOllamaClient] Detected: new article proposal")
            # Return article proposals for vault analysis
            return """[
  {
    "title": "Test Article 1",
    "category": "Testing",
    "description": "A test article for E2E testing",
    "filename": "test-article-1.md"
  }
]"""
        elif "create a comprehensive" in prompt.lower():
            print("[MockOllamaClient] Detected: article content generation")
            # Return article content for vault generation
            return """---
title: Test Article 1
category: Testing
created: 2025-10-10
---

# Test Article 1

This is a test article generated for E2E testing purposes.

## Introduction

This article serves as a placeholder for testing the workflow system.

## Content

- Point 1: Testing functionality
- Point 2: Ensuring proper integration
- Point 3: Validating mock responses

## Conclusion

The testing is complete.
"""
        else:
            print("[MockOllamaClient] Detected: default fallback")
            # Default fallback response
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
