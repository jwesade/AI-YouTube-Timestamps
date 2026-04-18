"""Orchestrates one end-to-end ingest run: fetch -> validate -> dedupe.

Writing to the database is not part of this module yet — it will be plugged in
once Supabase credentials are available. For now the pipeline returns a
PipelineReport that the CLI serialises to JSON.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ingest import sources
from ingest.dedupe import Cluster, dedupe
from ingest.models import FetchResult, SourceRecord
from ingest.validate import ValidationReport, validate

log = logging.getLogger(__name__)


@dataclass
class PipelineReport:
    started_at: datetime
    finished_at: datetime
    sources: list[str]
    fetches: list[FetchResult] = field(default_factory=list)
    validation: ValidationReport | None = None
    clusters: list[Cluster] = field(default_factory=list)

    @property
    def raw_count(self) -> int:
        return sum(f.count for f in self.fetches)

    @property
    def kept_count(self) -> int:
        return self.validation.kept_count if self.validation else 0

    @property
    def cluster_count(self) -> int:
        return len(self.clusters)

    @property
    def duplicates_removed(self) -> int:
        return self.kept_count - self.cluster_count

    def summary(self) -> dict[str, object]:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_s": (self.finished_at - self.started_at).total_seconds(),
            "sources": self.sources,
            "raw_records": self.raw_count,
            "after_validation": self.kept_count,
            "unique_courts": self.cluster_count,
            "duplicates_removed": self.duplicates_removed,
            "multi_source_courts": sum(1 for c in self.clusters if len(c.source_types) > 1),
        }


def run_pipeline(source_names: list[str]) -> PipelineReport:
    started = datetime.now(timezone.utc)
    fetches: list[FetchResult] = []
    all_records: list[SourceRecord] = []

    for name in source_names:
        log.info("fetching source: %s", name)
        result = sources.get(name).fetch()
        fetches.append(result)
        all_records.extend(result.records)

    validation = validate(all_records)
    clusters = dedupe(validation.kept)

    finished = datetime.now(timezone.utc)
    report = PipelineReport(
        started_at=started,
        finished_at=finished,
        sources=source_names,
        fetches=fetches,
        validation=validation,
        clusters=clusters,
    )
    log.info("pipeline done: %s", report.summary())
    return report
