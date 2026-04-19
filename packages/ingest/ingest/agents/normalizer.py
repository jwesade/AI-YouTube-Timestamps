"""Normalizer: turns a Cluster of SourceRecords into one canonical NormalizedCourt.

Deterministic merge fills in what it can; the LLM is only called when there's
ambiguity (conflicting names, weak/generic primary names that could be improved
from context) and a LLM client is provided. Keeps cost low and output
reproducible for the easy cases.

For Venues (groups of clusters at the same physical location), use
`normalize_venue` instead — it normalizes the venue's "best" cluster and
sets the canonical `court_count` from the actual number of pitches found.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ingest.dedupe import Cluster
from ingest.models import SourceRecord
from ingest.venues import Venue

if TYPE_CHECKING:
    from ingest.llm import LLMClient

log = logging.getLogger(__name__)


class NormalizedCourt(BaseModel):
    """The canonical shape written to the `courts` table."""

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
    confidence: float = Field(0.5, ge=0.0, le=1.0)


SYSTEM_PROMPT = (
    "You merge multiple listings of the same padel venue (from OSM, Google, "
    "booking sites) into one clean German-address record. Prefer specific over "
    "generic names. Trust Google Places address fields over OSM when both "
    "exist. If an operator field looks like marketing fluff ('der beste Padel "
    "Club'), leave it null. Never invent facts not present in the inputs."
)


def normalize(cluster: Cluster, llm: LLMClient | None = None) -> NormalizedCourt:
    """Merge a cluster. Uses the deterministic path unless LLM is provided AND
    the cluster has ambiguity worth resolving."""
    deterministic = _deterministic_merge(cluster)
    if llm is None or not _needs_llm(cluster):
        return deterministic

    try:
        return _llm_merge(cluster, llm, baseline=deterministic)
    except Exception:
        log.exception("LLM normalization failed, falling back to deterministic merge")
        return deterministic


def normalize_venue(venue: Venue, llm: LLMClient | None = None) -> NormalizedCourt:
    """Normalize a Venue: pick its best cluster, normalize that, then override
    `court_count` with the venue's actual pitch count."""
    primary_cluster = _venue_primary_cluster(venue)
    nc = normalize(primary_cluster, llm=llm)
    return nc.model_copy(update={"court_count": venue.court_count})


def _venue_primary_cluster(venue: Venue) -> Cluster:
    primary_record = venue.primary
    for cluster in venue.members:
        if cluster.primary is primary_record:
            return cluster
    # Defensive fallback: should never happen since venue.primary comes from members.
    return venue.members[0]


def _deterministic_merge(cluster: Cluster) -> NormalizedCourt:
    """Take the most complete record as the base, fill gaps from others, and
    derive a better name when the primary's name is too generic to be useful."""
    primary = cluster.primary
    merged: dict[str, object | None] = primary.model_dump()

    for record in cluster.records:
        if record is primary:
            continue
        for field_name in (
            "address",
            "city",
            "postal_code",
            "court_count",
            "indoor",
            "outdoor",
            "operator",
            "booking_url",
        ):
            if merged.get(field_name) in (None, ""):
                value = getattr(record, field_name)
                if value not in (None, ""):
                    merged[field_name] = value

    merged["name"] = _compose_name(
        name=str(merged.get("name") or ""),
        operator=_as_str(merged.get("operator")),
        city=_as_str(merged.get("city")),
        address=_as_str(merged.get("address")),
    )

    confidence = _confidence_from_cluster(cluster)
    return NormalizedCourt(
        name=str(merged["name"]),
        address=_as_str(merged.get("address")),
        city=_as_str(merged.get("city")),
        postal_code=_as_str(merged.get("postal_code")),
        country=str(merged.get("country") or "DE"),
        lat=float(merged["lat"]),  # type: ignore[arg-type]
        lng=float(merged["lng"]),  # type: ignore[arg-type]
        court_count=_as_int(merged.get("court_count")),
        indoor=_as_bool(merged.get("indoor")),
        outdoor=_as_bool(merged.get("outdoor")),
        operator=_as_str(merged.get("operator")),
        booking_url=_as_str(merged.get("booking_url")),
        confidence=confidence,
    )


# Patterns that make a name "weak": it tells a user nothing about the venue.
_WEAK_NAME_PATTERNS = (
    re.compile(r"^\s*$"),
    re.compile(r"^unbekannt", re.IGNORECASE),
    re.compile(r"^padel\s*(court|platz|anlage)?\s*$", re.IGNORECASE),
    re.compile(r"^court\s*\d+", re.IGNORECASE),
    re.compile(r"^\d+$"),  # just a number like "1"
    re.compile(r"^outdoor\s+\w+\s*\d*$", re.IGNORECASE),  # "Outdoor Spree 2"
    re.compile(r"^(cupra|oysho|heineken).*court", re.IGNORECASE),  # sponsored-court names
)


def _is_weak_name(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return True
    return any(p.search(name) for p in _WEAK_NAME_PATTERNS)


def _compose_name(
    *,
    name: str,
    operator: str | None,
    city: str | None,
    address: str | None,
) -> str:
    """Keep strong names as-is. For weak ones, synthesise something useful from
    operator/city/address so the venue isn't shown as 'Unbekannter Padel-Court'
    when we actually have enough context to name it."""
    if not _is_weak_name(name):
        return name.strip()
    if operator:
        if city and not operator.lower().endswith(city.lower()):
            return f"{operator} {city}"
        return operator
    if address and city:
        street = address.split(",")[0].strip()
        street = re.sub(r"\s*\d+[a-zA-Z-]*$", "", street).strip()  # drop house number
        if street:
            return f"Padel {city}, {street}"
        return f"Padel {city}"
    if city:
        return f"Padel {city}"
    return name.strip() or "Padel-Anlage"


def _needs_llm(cluster: Cluster) -> bool:
    """Call the LLM when there's ambiguity worth resolving:
      1) records disagree on the venue name, or
      2) the primary's name is still weak after deterministic composition
         but there's enough context (address/operator/city) to maybe do better.
    """
    names = {r.name.strip().lower() for r in cluster.records if r.name}
    if len(names) > 1:
        return True

    primary = cluster.primary
    if _is_weak_name(primary.name):
        has_context = any(
            getattr(r, f) for r in cluster.records for f in ("address", "city", "operator")
        )
        return has_context
    return False


def _llm_merge(
    cluster: Cluster, llm: LLMClient, *, baseline: NormalizedCourt
) -> NormalizedCourt:
    payload = [r.model_dump(mode="json") for r in cluster.records]
    user = (
        "Here are several records believed to describe the same padel venue. "
        "Produce the canonical merged record.\n\n"
        f"Baseline (from deterministic merge): {baseline.model_dump_json()}\n\n"
        f"Raw source records: {payload}"
    )
    return llm.structured(system=SYSTEM_PROMPT, user=user, schema=NormalizedCourt)


def _confidence_from_cluster(cluster: Cluster) -> float:
    """More confirming sources -> higher confidence, capped at 0.95."""
    base = 0.5
    bonus_per_source = 0.15
    return min(0.95, base + bonus_per_source * (len(cluster.source_types) - 1))


def _as_str(value: object | None) -> str | None:
    return str(value) if value not in (None, "") else None


def _as_int(value: object | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_bool(value: object | None) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


def _records_preview(records: list[SourceRecord]) -> list[dict]:  # pragma: no cover
    return [{"src": r.source_type, "name": r.name} for r in records]
