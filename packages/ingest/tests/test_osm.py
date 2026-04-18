"""Smoke tests for the OSM parser. The live Overpass API is not hit here."""

from __future__ import annotations

from ingest.sources.osm import _element_to_record

_NODE_FIXTURE = {
    "type": "node",
    "id": 12345,
    "lat": 52.5200,
    "lon": 13.4050,
    "tags": {
        "sport": "padel",
        "name": "Padel Base Berlin",
        "addr:street": "Hauptstrasse",
        "addr:housenumber": "1",
        "addr:city": "Berlin",
        "addr:postcode": "10115",
        "operator": "Padel Base GmbH",
        "website": "https://padelbase.example",
        "indoor": "yes",
        "sport:padel:courts": "4",
    },
}

_WAY_FIXTURE = {
    "type": "way",
    "id": 67890,
    "center": {"lat": 48.1351, "lon": 11.5820},
    "tags": {"sport": "padel", "name": "Padel Arena München"},
}


def test_node_parsed_with_full_address():
    record = _element_to_record(_NODE_FIXTURE)
    assert record is not None
    assert record.name == "Padel Base Berlin"
    assert record.lat == 52.52
    assert record.lng == 13.405
    assert record.address == "Hauptstrasse 1"
    assert record.city == "Berlin"
    assert record.postal_code == "10115"
    assert record.operator == "Padel Base GmbH"
    assert record.indoor is True
    assert record.court_count == 4
    assert record.source_ref == "node/12345"
    assert str(record.source_url).startswith("https://www.openstreetmap.org/node/12345")


def test_way_uses_center_coords():
    record = _element_to_record(_WAY_FIXTURE)
    assert record is not None
    assert record.lat == 48.1351
    assert record.lng == 11.5820
    assert record.source_ref == "way/67890"


def test_element_without_coords_is_skipped():
    broken = {"type": "node", "id": 1, "tags": {"sport": "padel", "name": "x"}}
    assert _element_to_record(broken) is None
