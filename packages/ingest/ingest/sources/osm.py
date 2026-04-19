"""OpenStreetMap source via the Overpass API.

Free, no API key, Creative Commons licensed. Good coverage of clubs that OSM
contributors have tagged; missing many commercial sites. Use as baseline.

The main Overpass instance (overpass-api.de) is frequently overloaded and a
Germany-wide query times out (504) regularly across all public mirrors.
We query each Bundesland separately so individual queries stay small enough
to slip through. Failures of single regions don't kill the whole run.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ingest.models import FetchResult, SourceRecord

log = logging.getLogger(__name__)

# Public Overpass mirrors, ordered by observed reliability.
OVERPASS_ENDPOINTS: tuple[str, ...] = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

# All 16 German Bundesländer by ISO 3166-2 code.
BUNDESLAND_ISO_CODES: tuple[str, ...] = (
    "DE-BW",  # Baden-Württemberg
    "DE-BY",  # Bayern
    "DE-BE",  # Berlin
    "DE-BB",  # Brandenburg
    "DE-HB",  # Bremen
    "DE-HH",  # Hamburg
    "DE-HE",  # Hessen
    "DE-MV",  # Mecklenburg-Vorpommern
    "DE-NI",  # Niedersachsen
    "DE-NW",  # Nordrhein-Westfalen
    "DE-RP",  # Rheinland-Pfalz
    "DE-SL",  # Saarland
    "DE-SN",  # Sachsen
    "DE-ST",  # Sachsen-Anhalt
    "DE-SH",  # Schleswig-Holstein
    "DE-TH",  # Thüringen
)

# Query template per Bundesland (ISO 3166-2 region). Smaller scope means
# faster execution and fewer 504s than a Germany-wide query.
OVERPASS_QUERY_REGION_TEMPLATE = """
[out:json][timeout:60];
area["ISO3166-2"="{iso}"][admin_level=4]->.region;
(
  nwr["sport"="padel"](area.region);
);
out center tags;
""".strip()

_RETRYABLE_STATUS = {429, 502, 503, 504}


class OSMSource:
    name = "osm"

    def __init__(
        self,
        endpoints: tuple[str, ...] = OVERPASS_ENDPOINTS,
        regions: tuple[str, ...] = BUNDESLAND_ISO_CODES,
        timeout: float = 90.0,
        polite_delay_s: float = 1.0,
    ):
        self._endpoints = endpoints
        self._regions = regions
        self._timeout = timeout
        self._polite_delay_s = polite_delay_s

    def fetch(self) -> FetchResult:
        log.info("fetching padel courts from OSM Overpass (%d Bundesländer)", len(self._regions))
        all_elements: list[dict[str, Any]] = []
        failed: list[tuple[str, str]] = []

        with httpx.Client(timeout=self._timeout, headers=self._headers()) as client:
            for iso in self._regions:
                query = OVERPASS_QUERY_REGION_TEMPLATE.format(iso=iso)
                try:
                    payload = self._request_with_failover(client, query, iso)
                    elements = payload.get("elements", [])
                    log.info("region %s: %d raw elements", iso, len(elements))
                    all_elements.extend(elements)
                except RuntimeError as exc:
                    log.warning("region %s failed: %s", iso, exc)
                    failed.append((iso, str(exc)))
                time.sleep(self._polite_delay_s)

        if failed and len(failed) == len(self._regions):
            raise RuntimeError(f"all {len(self._regions)} regions failed (Overpass overloaded?)")
        if failed:
            log.warning(
                "partial result: %d/%d regions failed: %s",
                len(failed),
                len(self._regions),
                [iso for iso, _ in failed],
            )

        records: list[SourceRecord] = []
        for element in all_elements:
            record = _element_to_record(element)
            if record is not None:
                records.append(record)

        log.info(
            "OSM total: %d raw elements across regions, %d valid records",
            len(all_elements),
            len(records),
        )
        return FetchResult(source_type="osm", records=records)

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "padel-atlas-de/0.1 (+https://github.com/jwesade/ai-youtube-timestamps)",
            "Accept": "application/json",
        }

    def _request_with_failover(
        self, client: httpx.Client, query: str, label: str
    ) -> dict[str, Any]:
        errors: list[tuple[str, Exception]] = []
        for endpoint in self._endpoints:
            try:
                log.debug("[%s] trying %s", label, endpoint)
                resp = client.post(endpoint, data={"data": query})
                if resp.status_code in _RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(
                        f"status {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                errors.append((endpoint, exc))
                time.sleep(1)
        detail = "; ".join(f"{url}: {err}" for url, err in errors)
        raise RuntimeError(f"all endpoints failed ({detail})")


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
        booking_url=_normalize_url(tags.get("website") or tags.get("contact:website")),
        raw=element,
    )


def _normalize_url(value: Any) -> str | None:
    """Coerce OSM website tags into proper URLs. OSM contributors commonly write
    'example.com' without a scheme, or leave junk like 'N/A'. Return None for
    anything that doesn't look like a real URL."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or " " in cleaned:
        return None
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    # Must contain a dot in the host portion.
    host = cleaned.split("://", 1)[1].split("/", 1)[0]
    if "." not in host:
        return None
    return cleaned


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
