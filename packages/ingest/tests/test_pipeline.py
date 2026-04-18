"""End-to-end pipeline tests using a fake in-process source."""

from __future__ import annotations

from ingest import sources
from ingest.models import FetchResult, SourceRecord
from ingest.pipeline import run_pipeline


class _FakeSource:
    name = "fake"

    def fetch(self) -> FetchResult:
        return FetchResult(
            source_type="manual",
            records=[
                SourceRecord(source_type="manual", name="Padel Base", lat=52.52, lng=13.40),
                SourceRecord(source_type="manual", name="Padel Base", lat=52.5201, lng=13.4001),
                SourceRecord(source_type="manual", name="Padel Arena", lat=48.13, lng=11.58),
                SourceRecord(source_type="manual", name="Nope", lat=48.8566, lng=2.3522),  # Paris
                SourceRecord(source_type="manual", name="", lat=52.5, lng=13.4),  # empty name
            ],
        )


def test_pipeline_end_to_end(monkeypatch):
    monkeypatch.setitem(sources.REGISTRY, "fake", _FakeSource)

    report = run_pipeline(["fake"])
    summary = report.summary()

    assert summary["raw_records"] == 5
    assert summary["after_validation"] == 3  # Paris + empty dropped
    assert summary["unique_courts"] == 2  # the two Padel Base dupes merged
    assert summary["duplicates_removed"] == 1
