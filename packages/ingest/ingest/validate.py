"""Validation rules applied to every SourceRecord before downstream steps.

Runs deterministic filters only — we want cheap, explainable rejection here.
Fuzzy decisions belong in the agent-based normaliser later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ingest.models import SourceRecord

log = logging.getLogger(__name__)

# Rough bounding box of Germany (generous on purpose to catch border-town records).
# minLng, minLat, maxLng, maxLat
DE_BBOX = (5.5, 47.2, 15.1, 55.1)


@dataclass(frozen=True)
class ValidationReport:
    kept: list[SourceRecord]
    dropped: list[tuple[SourceRecord, str]]

    @property
    def kept_count(self) -> int:
        return len(self.kept)

    @property
    def dropped_count(self) -> int:
        return len(self.dropped)


def validate(records: list[SourceRecord]) -> ValidationReport:
    kept: list[SourceRecord] = []
    dropped: list[tuple[SourceRecord, str]] = []
    for record in records:
        reason = _reject_reason(record)
        if reason is None:
            kept.append(record)
        else:
            dropped.append((record, reason))
    log.info("validation: kept %d, dropped %d", len(kept), len(dropped))
    return ValidationReport(kept=kept, dropped=dropped)


def _reject_reason(record: SourceRecord) -> str | None:
    if not record.name or not record.name.strip():
        return "empty name"
    if record.lat is None or record.lng is None:
        return "missing coordinates"
    if not _in_germany(record.lat, record.lng):
        return f"coordinates outside DE bbox ({record.lat:.4f}, {record.lng:.4f})"
    if record.country.upper() not in {"DE", "DEU", "GERMANY", "DEUTSCHLAND"}:
        return f"country={record.country!r}, not Germany"
    return None


def _in_germany(lat: float, lng: float) -> bool:
    min_lng, min_lat, max_lng, max_lat = DE_BBOX
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng
