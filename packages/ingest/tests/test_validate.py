from __future__ import annotations

from ingest.models import SourceRecord
from ingest.validate import validate


def _record(**overrides) -> SourceRecord:
    base = dict(
        source_type="osm",
        name="Padel Club",
        lat=52.5,
        lng=13.4,
    )
    base.update(overrides)
    return SourceRecord(**base)


def test_valid_record_kept():
    report = validate([_record()])
    assert report.kept_count == 1
    assert report.dropped_count == 0


def test_empty_name_dropped():
    report = validate([_record(name="   ")])
    assert report.kept_count == 0
    assert "empty name" in report.dropped[0][1]


def test_coords_outside_germany_dropped():
    # Paris
    report = validate([_record(lat=48.8566, lng=2.3522)])
    assert report.kept_count == 0
    assert "outside DE" in report.dropped[0][1]


def test_non_german_country_dropped():
    report = validate([_record(country="FR")])
    assert report.kept_count == 0


def test_alternate_spellings_accepted():
    for country in ("DE", "DEU", "Germany", "Deutschland"):
        report = validate([_record(country=country)])
        assert report.kept_count == 1, f"country={country}"
