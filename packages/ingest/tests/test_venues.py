from __future__ import annotations

from ingest.dedupe import Cluster
from ingest.models import SourceRecord
from ingest.venues import group_into_venues


def _r(name: str, lat: float, lng: float, *, leisure: str = "pitch", **extra) -> SourceRecord:
    return SourceRecord(
        source_type="osm",
        name=name,
        lat=lat,
        lng=lng,
        raw={"tags": {"leisure": leisure, "sport": "padel"}},
        **extra,
    )


def _c(record: SourceRecord) -> Cluster:
    return Cluster(records=[record])


def test_six_courts_at_one_venue_become_one_venue():
    # Berlin Tio Tio area: ~5 individual pitches within 10m of each other
    base_lat, base_lng = 52.5040, 13.4733
    courts = [
        _r("CUPRA Court 3", base_lat, base_lng + 0.0000),
        _r("CUPRA Center Court 1", base_lat, base_lng + 0.0001),
        _r("CUPRA Center Court 2", base_lat, base_lng + 0.0002),
        _r("OYSHO Court 4", base_lat, base_lng - 0.0001),
        _r("Heineken 0,0 Court 5", base_lat, base_lng - 0.0002),
        _r("Tio Tio", base_lat, base_lng, leisure="sports_centre"),
    ]
    venues = group_into_venues([_c(r) for r in courts])
    assert len(venues) == 1
    assert venues[0].court_count == 5  # 5 pitches
    assert venues[0].primary.name == "Tio Tio"  # sports_centre wins as primary


def test_far_apart_venues_stay_separate():
    venues = group_into_venues([
        _c(_r("Padel Berlin", 52.5077, 13.4740)),
        _c(_r("Padel München", 48.1351, 11.5820)),
    ])
    assert len(venues) == 2


def test_unbekannt_record_alone_becomes_its_own_venue():
    venues = group_into_venues([_c(_r("Unbekannter Padel-Court", 51.0, 7.0))])
    assert len(venues) == 1
    assert venues[0].court_count == 1


def test_unbekannt_absorbed_into_named_venue_if_close():
    venues = group_into_venues([
        _c(_r("Padel Base", 51.0, 7.0, leisure="sports_centre")),
        _c(_r("Unbekannter Padel-Court", 51.00005, 7.00005)),  # ~7m away
    ])
    assert len(venues) == 1
    assert venues[0].primary.name == "Padel Base"
    assert venues[0].court_count == 1  # only 1 pitch (the Unbekannt one)


def test_named_pitch_beats_unbekannt_for_primary():
    venues = group_into_venues([
        _c(_r("Unbekannter Padel-Court", 51.0, 7.0)),
        _c(_r("Lucky Star Padel", 51.00005, 7.00005)),
    ])
    assert len(venues) == 1
    assert venues[0].primary.name == "Lucky Star Padel"


def test_address_breaks_ties_when_no_real_venue_record():
    venues = group_into_venues([
        _c(_r("Padel Court", 51.0, 7.0)),
        _c(_r("Padel Court", 51.00005, 7.00005, address="Hauptstraße 1")),
    ])
    assert len(venues) == 1
    assert venues[0].primary.address == "Hauptstraße 1"
