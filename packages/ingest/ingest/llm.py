"""Thin wrapper around the Anthropic SDK for structured, one-shot completions.

Used by the normalizer and other small LLM-backed helpers where we don't need
the full Claude Agent SDK (tool loops, sub-agents). Those live in ingest/agents/.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

from ingest.config import require, settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def structured(self, *, system: str, user: str, schema: type[T]) -> T: ...


class AnthropicClient:
    """Production client. Calls the Anthropic Messages API and parses JSON output."""

    def __init__(self, model: str | None = None):
        self._client = Anthropic(api_key=require("anthropic_api_key"))
        self._model = model or settings().llm_model

    def structured(self, *, system: str, user: str, schema: type[T]) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        prompt = (
            f"{user}\n\n"
            "Respond with **only** a JSON object matching this schema. "
            "No preamble, no markdown fences.\n\n"
            f"<schema>\n{schema_json}\n</schema>"
        )
        resp = self._client.messages.create(
            model=self._model,
            system=system,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text").strip()
        text = _strip_fences(text)
        log.debug("LLM raw response: %s", text)
        return schema.model_validate_json(text)


def _strip_fences(text: str) -> str:
    """Trim ```json ... ``` fences if the model adds them despite the instruction."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()
