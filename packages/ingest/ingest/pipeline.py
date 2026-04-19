"""Orchestrates one end-to-end ingest run.

Steps: fetch -> validate -> dedupe -> group_into_venues -> (normalize) -> (write).

Normalize and write are opt-in so the pipeline stays useful locally without
API keys or DB credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ingest import sources
from ingest.agents.normalizer import NormalizedCourt, normalize_venue
from ingest.dedupe import Cluster, dedupe
from ingest.models import FetchResult, SourceRecord
from ingest.validate import ValidationReport, validate
from ingest.venues import Venue, group_into_venues

log = logging.getLogger(__name__)


@dataclass
class PipelineReport:
    started_at: datetime
    finished_at: datetime
    sources: list[str]
    fetches: list[FetchResult] = field(default_factory=list)
    validation: ValidationReport | None = None
    clusters: list[Cluster] = field(default_factory=list)
    venues: list[Venue] = field(default_factory=list)
    normalized: list[NormalizedCourt] = field(default_factory=list)
    write_stats: dict[str, int] | None = None

    @property
    def raw_count(self) -> int:
        return sum(f.count for f in self.fetches)

    @property
    def kept_count(self) -> int:
        return self.validation.kept_count if self.validation else 0

    def summary(self) -> dict[str, object]:
        out: dict[str, object] = {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_s": (self.finished_at - self.started_at).total_seconds(),
            "sources": self.sources,
            "raw_records": self.raw_count,
            "after_validation": self.kept_count,
            "clusters": len(self.clusters),
            "venues": len(self.venues),
            "courts_total": sum(v.court_count for v in self.venues),
            "multi_court_venues": sum(1 for v in self.venues if v.court_count > 1),
            "multi_source_venues": sum(1 for v in self.venues if len(v.source_types) > 1),
            "normalized": len(self.normalized),
        }
        if self.write_stats is not None:
            out["write_stats"] = self.write_stats
        return out


def run_pipeline(
    source_names: list[str],
    *,
    use_llm: bool = False,
    write_to_db: bool = False,
) -> PipelineReport:
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
    venues = group_into_venues(clusters)

    llm = _build_llm() if use_llm else None
    normalized = [normalize_venue(v, llm=llm) for v in venues]

    write_stats: dict[str, int] | None = None
    if write_to_db:
        write_stats = _write(venues, normalized)

    finished = datetime.now(timezone.utc)
    report = PipelineReport(
        started_at=started,
        finished_at=finished,
        sources=source_names,
        fetches=fetches,
        validation=validation,
        clusters=clusters,
        venues=venues,
        normalized=normalized,
        write_stats=write_stats,
    )
    log.info("pipeline done: %s", report.summary())
    return report


def _build_llm():
    from ingest.llm import AnthropicClient  # local import so tests don't need the key

    return AnthropicClient()


def _write(venues: list[Venue], normalized: list[NormalizedCourt]) -> dict[str, int]:
    from ingest.config import require
    from ingest.writer.supabase import write_venues

    stats = write_venues(venues, normalized, db_url=require("supabase_db_url"))
    return {
        "venues_inserted": stats.venues_inserted,
        "sources_inserted": stats.sources_inserted,
    }
