"""Deterministic deduplication of SourceRecords from multiple sources.

Two records are considered the same physical venue when BOTH:
  - their coordinates are within `distance_m` meters (default 150m), AND
  - their normalised names have a token-set Jaccard similarity >= `name_threshold`.

This is intentionally conservative: we'd rather leave two near-duplicates as
separate courts than merge two legitimately different venues. A second, fuzzier
pass backed by a Claude agent will catch the rest once we wire it in.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field

from slugify import slugify

from ingest.models import SourceRecord

log = logging.getLogger(__name__)

DEFAULT_DISTANCE_M = 150.0
DEFAULT_NAME_THRESHOLD = 0.6

# Words that add noise to name matching ("Padel Club X" vs. "X Padel" should match).
_STOPWORDS = frozenset(
    {
        "padel",
        "club",
        "center",
        "centre",
        "arena",
        "halle",
        "sports",
        "sport",
        "gmbh",
        "ev",
        "e-v",
        "by",
        "the",
        "der",
        "die",
        "das",
        "de",
    }
)


@dataclass
class Cluster:
    """A group of SourceRecords believed to be the same physical venue."""

    records: list[SourceRecord] = field(default_factory=list)

    @property
    def primary(self) -> SourceRecord:
        # Prefer records with more data filled in.
        return max(self.records, key=_record_completeness)

    @property
    def source_types(self) -> set[str]:
        return {r.source_type for r in self.records}


def dedupe(
    records: list[SourceRecord],
    *,
    distance_m: float = DEFAULT_DISTANCE_M,
    name_threshold: float = DEFAULT_NAME_THRESHOLD,
) -> list[Cluster]:
    clusters: list[Cluster] = []
    for record in records:
        match = _find_match(record, clusters, distance_m, name_threshold)
        if match is None:
            clusters.append(Cluster(records=[record]))
        else:
            match.records.append(record)
    log.info("dedupe: %d records -> %d clusters", len(records), len(clusters))
    return clusters


def _find_match(
    record: SourceRecord,
    clusters: list[Cluster],
    distance_m: float,
    name_threshold: float,
) -> Cluster | None:
    record_tokens = _name_tokens(record.name)
    for cluster in clusters:
        existing = cluster.records[0]
        if _haversine_m(record.lat, record.lng, existing.lat, existing.lng) > distance_m:
            continue
        if _jaccard(record_tokens, _name_tokens(existing.name)) >= name_threshold:
            return cluster
    return None


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * earth_r * math.asin(math.sqrt(a))


def _name_tokens(name: str) -> frozenset[str]:
    slug = slugify(name, lowercase=True, separator=" ")
    tokens = [t for t in re.split(r"\s+", slug) if t and t not in _STOPWORDS]
    return frozenset(tokens)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _record_completeness(record: SourceRecord) -> int:
    score = 0
    for attr in ("address", "postal_code", "city", "court_count", "operator", "booking_url"):
        if getattr(record, attr):
            score += 1
    if record.indoor is not None:
        score += 1
    return score
