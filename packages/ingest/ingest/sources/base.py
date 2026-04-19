"""Source protocol: every fetcher returns a FetchResult."""

from __future__ import annotations

from typing import Protocol

from ingest.models import FetchResult


class Source(Protocol):
    name: str

    def fetch(self) -> FetchResult: ...
