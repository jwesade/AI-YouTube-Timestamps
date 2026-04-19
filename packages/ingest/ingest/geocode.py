"""Reverse geocoding via Nominatim (OpenStreetMap's geocoder).

Nominatim is free, no API key needed, and uses the same underlying OSM data
as our main source — so the city and postal code it returns are consistent
with what we'd get from a named OSM record.

Usage policy: 1 request/second max, meaningful User-Agent, batch-friendly
applications are asked to self-host if they go past a few thousand requests
per day. 80 venues in one run is fine; if we add more sources, we self-host.
https://operations.osmfoundation.org/policies/nominatim/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_USER_AGENT = "padel-atlas-de/0.1 (+https://github.com/jwesade/ai-youtube-timestamps)"


@dataclass(frozen=True)
class ReverseResult:
    address: str | None
    city: str | None
    postal_code: str | None
    country: str | None


class NominatimGeocoder:
    def __init__(
        self,
        endpoint: str = NOMINATIM_URL,
        timeout: float = 10.0,
        min_interval_s: float = 1.0,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._min_interval_s = min_interval_s
        self._last_request_ts: float = 0.0

    def reverse(self, lat: float, lng: float) -> ReverseResult | None:
        self._throttle()
        params = {
            "lat": f"{lat:.7f}",
            "lon": f"{lng:.7f}",
            "format": "jsonv2",
            "addressdetails": 1,
            "accept-language": "de",
            "zoom": 18,
        }
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        try:
            with httpx.Client(timeout=self._timeout, headers=headers) as client:
                resp = client.get(self._endpoint, params=params)
                resp.raise_for_status()
                return parse_nominatim_response(resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("reverse geocoding failed for (%.4f, %.4f): %s", lat, lng, exc)
            return None

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self._min_interval_s - (now - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_request_ts = time.monotonic()


def parse_nominatim_response(payload: Any) -> ReverseResult | None:
    """Extract the fields we care about from a Nominatim JSON response."""
    if not isinstance(payload, dict):
        return None
    addr = payload.get("address") or {}
    if not isinstance(addr, dict):
        return None

    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("suburb")
        or addr.get("city_district")
    )
    street = addr.get("road")
    housenumber = addr.get("house_number")
    if street and housenumber:
        address = f"{street} {housenumber}"
    else:
        address = street

    result = ReverseResult(
        address=address,
        city=city,
        postal_code=addr.get("postcode"),
        country=(addr.get("country_code") or "").upper() or None,
    )
    if not any((result.address, result.city, result.postal_code)):
        return None
    return result
