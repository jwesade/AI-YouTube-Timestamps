"""Writes normalized venues into Supabase (Postgres) via psycopg.

v0 strategy: truncate-and-reload. Simple and idempotent. Once we have manual
annotations or multiple overlapping ingests, we upgrade to upsert on
(source_type, source_ref) + court linkage by spatial proximity.

One row in `courts` per Venue (a physical location). One row in `sources` per
raw scraped record across all member clusters of the venue, preserving full
provenance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb

from ingest.agents.normalizer import NormalizedCourt
from ingest.venues import Venue

log = logging.getLogger(__name__)


@dataclass
class WriteStats:
    venues_inserted: int
    sources_inserted: int


def write_venues(
    venues: list[Venue],
    normalized: list[NormalizedCourt],
    db_url: str,
) -> WriteStats:
    if len(venues) != len(normalized):
        raise ValueError(
            f"venues/normalized length mismatch: {len(venues)} vs {len(normalized)}"
        )

    venues_inserted = 0
    sources_inserted = 0
    log.info("writing %d venues to Supabase", len(venues))

    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE sources, courts RESTART IDENTITY CASCADE")

        for venue, nc in zip(venues, normalized, strict=True):
            cur.execute(
                """
                INSERT INTO courts (
                    name, address, city, postal_code, country,
                    lat, lng, court_count, indoor, outdoor,
                    booking_url, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    nc.name,
                    nc.address,
                    nc.city,
                    nc.postal_code,
                    nc.country,
                    nc.lat,
                    nc.lng,
                    nc.court_count,
                    nc.indoor,
                    nc.outdoor,
                    nc.booking_url,
                    nc.confidence,
                ),
            )
            court_id = cur.fetchone()[0]
            venues_inserted += 1

            for cluster in venue.members:
                for record in cluster.records:
                    cur.execute(
                        """
                        INSERT INTO sources (
                            court_id, source_type, source_ref, source_url, raw_data
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            court_id,
                            record.source_type,
                            record.source_ref,
                            str(record.source_url) if record.source_url else None,
                            Jsonb(record.raw),
                        ),
                    )
                    sources_inserted += 1

        conn.commit()

    log.info("wrote %d venues, %d source rows", venues_inserted, sources_inserted)
    return WriteStats(venues_inserted=venues_inserted, sources_inserted=sources_inserted)
