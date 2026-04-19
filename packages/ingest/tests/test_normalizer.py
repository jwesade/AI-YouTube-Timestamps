from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from ingest.agents.normalizer import NormalizedCourt, normalize
from ingest.dedupe import Cluster
from ingest.models import SourceRecord

T = TypeVar("T", bound=BaseModel)


def _r(name: str, source_type: str = "osm", **extra) -> SourceRecord:
    base = dict(source_type=source_type, name=name, lat=52.52, lng=13.40)
    base.update(extra)
    return SourceRecord(**base)


class _FakeLLM:
    def __init__(self, response: NormalizedCourt):
        self._response = response
        self.calls = 0

    def structured(self, *, system, user, schema):
        self.calls += 1
        return self._response


def test_deterministic_merge_prefers_complete_record():
    cluster = Cluster(
        records=[
            _r("Padel Club X"),
            _r(
                "Padel Club X",
                source_type="google_places",
                address="Hauptstr. 1",
                city="Berlin",
                postal_code="10115",
                court_count=4,
            ),
        ]
    )
    result = normalize(cluster)
    assert result.address == "Hauptstr. 1"
    assert result.city == "Berlin"
    assert result.court_count == 4


def test_confidence_scales_with_source_count():
    one = normalize(Cluster(records=[_r("X")]))
    two = normalize(Cluster(records=[_r("X"), _r("X", source_type="google_places")]))
    assert two.confidence > one.confidence


def test_llm_skipped_when_names_agree():
    cluster = Cluster(records=[_r("Padel X"), _r("Padel X", source_type="google_places")])
    fake = _FakeLLM(NormalizedCourt(name="ignored", lat=0, lng=0))
    normalize(cluster, llm=fake)
    assert fake.calls == 0


def test_llm_called_when_names_disagree():
    cluster = Cluster(
        records=[
            _r("Padel Base Berlin"),
            _r("PadelBase Berlin Mitte", source_type="google_places"),
        ]
    )
    expected = NormalizedCourt(name="Padel Base Berlin Mitte", lat=52.52, lng=13.40)
    fake = _FakeLLM(expected)
    result = normalize(cluster, llm=fake)
    assert fake.calls == 1
    assert result.name == "Padel Base Berlin Mitte"


def test_llm_failure_falls_back_to_deterministic():
    cluster = Cluster(records=[_r("Padel A"), _r("Padel B", source_type="google_places")])

    class _BrokenLLM:
        def structured(self, **_):
            raise RuntimeError("boom")

    result = normalize(cluster, llm=_BrokenLLM())
    assert result.name in {"Padel A", "Padel B"}  # deterministic primary survives
