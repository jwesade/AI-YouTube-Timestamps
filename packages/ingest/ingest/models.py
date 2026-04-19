"""Pydantic models shared between sources, normaliser, and DB writer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal[
    "osm",
    "google_places",
    "playtomic",
    "matchi",
    "dpv",
    "padel_atlas",
    "manual",
]


class SourceRecord(BaseModel):
    """One raw record from an external source. Produced by a fetcher."""

    source_type: SourceType
    source_ref: str | None = None
    source_url: str | None = None
    name: str
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "DE"
    lat: float
    lng: float
    court_count: int | None = None
    indoor: bool | None = None
    outdoor: bool | None = None
    operator: str | None = None
    booking_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FetchResult(BaseModel):
    """Wrapper returned by every source fetcher."""

    source_type: SourceType
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    records: list[SourceRecord]

    @property
    def count(self) -> int:
        return len(self.records)
