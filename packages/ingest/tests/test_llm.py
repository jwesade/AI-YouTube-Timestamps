"""Tests for the Anthropic-backed LLM wrapper. The real API is not called."""

from __future__ import annotations

from pydantic import BaseModel

from ingest.llm import _strip_fences


class _Out(BaseModel):
    answer: str


def test_strip_fences_removes_markdown_code_block():
    raw = '```json\n{"answer": "hi"}\n```'
    assert _strip_fences(raw) == '{"answer": "hi"}'


def test_strip_fences_handles_plain_json():
    assert _strip_fences('{"answer": "hi"}') == '{"answer": "hi"}'


def test_strip_fences_handles_typeless_fence():
    raw = '```\n{"answer": "hi"}\n```'
    assert _strip_fences(raw) == '{"answer": "hi"}'
