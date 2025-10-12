"""Shared utilities for LLM client implementations."""

from __future__ import annotations

import json
from typing import Any, Iterable, Tuple


def parse_structured_response(response: str) -> Any:
    """
    Attempt to parse a JSON-like structure from an LLM response.

    The function first tries to parse the entire response as JSON. If that
    fails, it attempts to extract the first JSON object or array found within
    the response text.

    Args:
        response: Raw string returned by an LLM.

    Returns:
        Parsed Python data structure.

    Raises:
        ValueError: If no valid JSON payload can be extracted.
    """
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    candidates: Iterable[Tuple[int, str, str]] = (
        (response.find("{"), "{", "}"),
        (response.find("["), "[", "]"),
    )

    for start_index, opening, closing in sorted(
        (c for c in candidates if c[0] != -1), key=lambda item: item[0]
    ):
        end_index = response.rfind(closing)
        if end_index == -1 or end_index <= start_index:
            continue

        snippet = response[start_index : end_index + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            continue

    raise ValueError("Unable to parse LLM response as valid JSON.")
