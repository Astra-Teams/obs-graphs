"""LLM client implementation backed by the MLX runtime."""

from __future__ import annotations

import logging
from threading import Lock
from typing import Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from src.obs_graphs.clients._llm_utils import parse_structured_response
from src.obs_graphs.config.mlx_settings import MLXSettings
from src.obs_graphs.protocols.llm_client_protocol import LLMClientProtocol

logger = logging.getLogger(__name__)

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class MLXClient(LLMClientProtocol):
    """Client that generates completions using the MLX local runtime."""

    def __init__(self, mlx_settings: MLXSettings) -> None:
        self._model_name = mlx_settings.model
        self._max_tokens = mlx_settings.max_tokens
        self._temperature = mlx_settings.temperature
        self._top_p = mlx_settings.top_p
        self._model_lock = Lock()
        self._model_bundle: Optional[Tuple[object, object]] = None

    def invoke(self, prompt: str) -> str:
        """Execute the prompt via MLX and return the raw text."""
        logger.debug("Invoking MLX model '%s'", self._model_name)
        model, tokenizer = self._ensure_model_loaded()

        try:
            from mlx_lm import generate  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError(
                "MLX backend requires the 'mlx-lm' package. "
                "Install it via `pip install mlx-lm`."
            ) from exc

        result = generate(
            model,
            tokenizer,
            prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            top_p=self._top_p,
            verbose=False,
        )

        try:
            choices = result["choices"]
            if not choices:
                raise ValueError("MLX generation returned no choices.")
            text = choices[0].get("text")
            if not isinstance(text, str):
                raise ValueError("MLX generation returned non-string text.")
            return text
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid MLX generation response: {exc}") from exc

    def invoke_as_structured_output(
        self,
        prompt: str,
        schema: Type[StructuredModelT],
    ) -> StructuredModelT:
        """Execute the prompt and parse the response into the provided schema."""
        raw_response = self.invoke(prompt)
        payload = parse_structured_response(raw_response)
        return schema.model_validate(payload)

    def _ensure_model_loaded(self) -> Tuple[object, object]:
        """Load the MLX model lazily and cache it for subsequent invocations."""
        if self._model_bundle is not None:
            return self._model_bundle

        with self._model_lock:
            if self._model_bundle is not None:
                return self._model_bundle

            try:
                from mlx_lm import load  # type: ignore
            except (
                ImportError
            ) as exc:  # pragma: no cover - depends on optional dependency
                raise RuntimeError(
                    "MLX backend requires the 'mlx-lm' package. "
                    "Install it via `pip install mlx-lm`."
                ) from exc

            logger.info("Loading MLX model '%s'...", self._model_name)
            self._model_bundle = load(self._model_name)
            return self._model_bundle
