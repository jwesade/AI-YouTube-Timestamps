# packages/ingest

Python pipeline that fetches padel court data from public sources and (later) writes it into Supabase.

## Architecture

```
[Source Fetchers]  →  [Normalizer Agent]  →  [Geocoder]  →  [Deduper]  →  [Supabase]
     (deterministic)      (Claude Haiku)     (determ.)       (Haiku)       (Postgres)
```

v0 (this iteration) only implements the leftmost step — source fetchers. They write raw snapshots to `./data/*.json` so we can eyeball the data quality before connecting a database.

## Sources

| source        | status     | API key needed     | notes                             |
|---------------|------------|--------------------|-----------------------------------|
| `osm`         | ✅ ready   | no                 | OpenStreetMap via Overpass API    |
| `google_places` | planned  | yes (Google Cloud) | best coverage, most accurate      |
| `playtomic`   | planned    | no (scrape)        | covers most commercial clubs      |
| `matchi`      | planned    | no (scrape)        | complements Playtomic             |
| `dpv`         | planned    | no                 | Deutscher Padel Verband members   |

## Run locally

```bash
cd packages/ingest
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m ingest run --source osm
# → ./data/courts_osm.json  (≈50–200 records)
```

## Project layout

```
ingest/
  __init__.py
  __main__.py        → python -m ingest
  cli.py             → typer commands (run, list-sources)
  models.py          → SourceRecord, FetchResult (pydantic)
  sources/
    __init__.py      → REGISTRY of sources
    base.py          → Source protocol
    osm.py           → Overpass API fetcher
data/                → output snapshots (gitignored)
```

## Next steps

1. Add `google_places` source once the Google Cloud key is available.
2. Add the normalizer agent (Claude Haiku) to merge records from multiple sources.
3. Add a `db write` command that bulk-upserts into Supabase via the schema in `packages/db/schema.sql`.
