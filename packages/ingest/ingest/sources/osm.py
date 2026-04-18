"""OpenStreetMap source via the Overpass API.

Free, no API key, Creative Commons licensed. Good coverage of clubs that OSM
contributors have tagged; missing many commercial sites. Use as baseline.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ingest.models import FetchResult, SourceRecord

log = logging.getLogger(__name__)

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"

# Any OSM node/way/relation tagged sport=padel inside Germany.
OVERPASS_QUERY_DE = """
[out:json][timeout:180];
area["ISO3166-1"="DE"][admin_level=2]->.de;
(
  nwr["sport"="padel"](area.de);
);
out center tags;
""".strip()


class OSMSource:
    name = "osm"

    def __init__(self, endpoint: str = OVERPASS_ENDPOINT, timeout: float = 200.0):
        self._endpoint = endpoint
        self._timeout = timeout

    def fetch(self) -> FetchResult:
        log.info("fetching padel courts from OSM Overpass (DE)")
        headers = {
            "User-Agent": "padel-atlas-de/0.1 (+https://github.com/jwesade/ai-youtube-timestamps)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=self._timeout, headers=headers) as client:
            resp = client.post(self._endpoint, data={"data": OVERPASS_QUERY_DE})
            resp.raise_for_status()
            payload = resp.json()

        records: list[SourceRecord] = []
        for element in payload.get("elements", []):
            record = _element_to_record(element)
            if record is not None:
                records.append(record)

        log.info("OSM returned %d elements, kept %d records", len(payload.get("elements", [])), len(records))
        return FetchResult(source_type="osm", records=records)


def _element_to_record(element: dict[str, Any]) -> SourceRecord | None:
    tags = element.get("tags") or {}
    lat, lng = _coords(element)
    if lat is None or lng is None:
        return None

    name = tags.get("name") or tags.get("operator") or "Unbekannter Padel-Court"
    court_count = _safe_int(tags.get("sport:padel:courts") or tags.get("courts"))
    indoor, outdoor = _indoor_outdoor(tags)
    osm_type = element.get("type", "node")
    osm_id = element.get("id")
    source_ref = f"{osm_type}/{osm_id}" if osm_id is not None else None
    source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_id is not None else None

    return SourceRecord(
        source_type="osm",
        source_ref=source_ref,
        source_url=source_url,
        name=name,
        address=_address_from_tags(tags),
        city=tags.get("addr:city"),
        postal_code=tags.get("addr:postcode"),
        country=(tags.get("addr:country") or "DE").upper(),
        lat=lat,
        lng=lng,
        court_count=court_count,
        indoor=indoor,
        outdoor=outdoor,
        operator=tags.get("operator"),
        booking_url=tags.get("website") or tags.get("contact:website"),
        raw=element,
    )


def _coords(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if element.get("type") == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def _address_from_tags(tags: dict[str, Any]) -> str | None:
    street = tags.get("addr:street")
    number = tags.get("addr:housenumber")
    if street and number:
        return f"{street} {number}"
    return street


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _indoor_outdoor(tags: dict[str, Any]) -> tuple[bool | None, bool | None]:
    indoor_tag = tags.get("indoor")
    covered = tags.get("covered")
    if indoor_tag == "yes" or covered == "yes":
        return True, None
    if indoor_tag == "no" and covered in (None, "no"):
        return False, True
    return None, None
