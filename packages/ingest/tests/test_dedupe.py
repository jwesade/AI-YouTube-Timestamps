from __future__ import annotations

from ingest.dedupe import dedupe
from ingest.models import SourceRecord


def _r(name: str, lat: float, lng: float, source_type: str = "osm", **extra) -> SourceRecord:
    return SourceRecord(source_type=source_type, name=name, lat=lat, lng=lng, **extra)


def test_identical_records_from_two_sources_merged():
    records = [
        _r("Padel Base Berlin", 52.5200, 13.4050, source_type="osm"),
        _r("Padel Base Berlin", 52.5200, 13.4050, source_type="google_places"),
    ]
    clusters = dedupe(records)
    assert len(clusters) == 1
    assert clusters[0].source_types == {"osm", "google_places"}


def test_nearby_courts_with_similar_names_merged():
    # Same club, slightly different naming + 30m apart.
    records = [
        _r("Padel Club Berlin", 52.5200, 13.4050),
        _r("Padel Berlin Club", 52.52027, 13.40520),
    ]
    clusters = dedupe(records)
    assert len(clusters) == 1


def test_different_venues_same_city_not_merged():
    records = [
        _r("Padel Base", 52.5200, 13.4050),
        _r("Padel Arena Kreuzberg", 52.4990, 13.4030),  # ~2km away, different name
    ]
    clusters = dedupe(records)
    assert len(clusters) == 2


def test_same_location_different_names_not_merged():
    # Coin spot with two totally different sports venues — should stay apart.
    records = [
        _r("Padel Base", 52.5200, 13.4050),
        _r("Tennis Club Mitte", 52.5200, 13.4050),
    ]
    clusters = dedupe(records)
    assert len(clusters) == 2


def test_primary_prefers_more_complete_record():
    sparse = _r("Padel Club X", 52.5, 13.4)
    rich = _r(
        "Padel Club X",
        52.5,
        13.4,
        source_type="google_places",
        address="Hauptstrasse 1",
        city="Berlin",
        postal_code="10115",
        court_count=4,
        operator="Padel X GmbH",
    )
    clusters = dedupe([sparse, rich])
    assert len(clusters) == 1
    assert clusters[0].primary is rich
