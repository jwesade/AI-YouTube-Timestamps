"""Group spatially-close clusters into venues.

A venue is a physical location (a club, a sports hall) that may host several
individual padel courts (pitches). OSM contributors often map each pitch as a
separate way/node, plus sometimes the surrounding sports_centre as another
record. We group all of these into one Venue so the resulting `courts` row
represents a real-world location, not an individual playing field.

Distance-only grouping by design — name-based grouping was already done in
`dedupe`. Here we want to merge "Tio Tio" + "CUPRA Court 3" + "OYSHO Court 4"
into a single venue purely because they share a footprint.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from ingest.dedupe import Cluster
from ingest.models import SourceRecord

log = logging.getLogger(__name__)

DEFAULT_VENUE_DISTANCE_M = 80.0


@dataclass
class Venue:
    """One physical place that hosts one or more padel courts."""

    members: list[Cluster] = field(default_factory=list)

    @property
    def primary(self) -> SourceRecord:
        """Pick the most "venue-like" record across all member clusters."""
        candidates = [c.primary for c in self.members]
        return max(candidates, key=_venue_score)

    @property
    def court_count(self) -> int:
        """Estimated number of physical courts at this venue.

        We count members tagged as `leisure=pitch`; if none are pitches (e.g.
        the venue is only mapped as a sports_centre point), we fall back to
        the explicit `court_count` on the primary, or to `1`.
        """
        pitch_count = sum(1 for c in self.members if _is_pitch(c.primary))
        if pitch_count > 0:
            return pitch_count
        if self.primary.court_count:
            return self.primary.court_count
        return 1

    @property
    def source_types(self) -> set[str]:
        types: set[str] = set()
        for c in self.members:
            types.update(c.source_types)
        return types


def group_into_venues(
    clusters: list[Cluster],
    *,
    distance_m: float = DEFAULT_VENUE_DISTANCE_M,
) -> list[Venue]:
    """Greedy single-pass spatial grouping. First venue within reach wins."""
    venues: list[Venue] = []
    for cluster in clusters:
        primary = cluster.primary
        match = _find_venue(primary, venues, distance_m)
        if match is None:
            venues.append(Venue(members=[cluster]))
        else:
            match.members.append(cluster)
    log.info("venue grouping: %d clusters -> %d venues", len(clusters), len(venues))
    return venues


def _find_venue(record: SourceRecord, venues: list[Venue], distance_m: float) -> Venue | None:
    for venue in venues:
        for cluster in venue.members:
            existing = cluster.primary
            d = _haversine_m(record.lat, record.lng, existing.lat, existing.lng)
            if d <= distance_m:
                return venue
    return None


def _venue_score(record: SourceRecord) -> tuple[int, int, int, int, int]:
    """Higher tuple wins. Picks the most "venue-like" record."""
    leisure = _osm_leisure(record)
    is_venue_building = int(leisure in {"sports_centre", "sports_hall"})
    has_real_name = int(bool(record.name) and "Unbekannt" not in record.name)
    has_address = int(bool(record.address))
    has_operator = int(bool(record.operator))
    completeness = _completeness(record)
    return (is_venue_building, has_real_name, has_address, has_operator, completeness)


def _is_pitch(record: SourceRecord) -> bool:
    return _osm_leisure(record) == "pitch"


def _osm_leisure(record: SourceRecord) -> str:
    raw = record.raw or {}
    if not isinstance(raw, dict):
        return ""
    tags: Any = raw.get("tags") or {}
    if not isinstance(tags, dict):
        return ""
    return tags.get("leisure", "") or ""


def _completeness(record: SourceRecord) -> int:
    score = 0
    for attr in ("address", "city", "postal_code", "court_count", "operator", "booking_url"):
        if getattr(record, attr):
            score += 1
    return score


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * earth_r * math.asin(math.sqrt(a))
