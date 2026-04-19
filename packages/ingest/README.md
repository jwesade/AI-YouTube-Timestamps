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
pip install -e ".[dev]"
cp .env.example .env    # then fill in SUPABASE_DB_URL and ANTHROPIC_API_KEY

# 1) Single source, raw snapshot (no keys needed):
python -m ingest run --source osm

# 2) Full pipeline, offline (no keys needed):
python -m ingest pipeline --source osm
#   → ./data/pipeline_summary.json + ./data/courts_clustered.json
#   → normalizer runs in its deterministic branch only

# 3) Full pipeline + LLM normalization for ambiguous clusters:
python -m ingest pipeline --source osm --normalize
#   needs ANTHROPIC_API_KEY in .env

# 4) Full pipeline -> write to Supabase:
python -m ingest pipeline --source osm --normalize --write
#   needs SUPABASE_DB_URL and ANTHROPIC_API_KEY in .env
```

Run tests + linter:

```bash
pytest -q
ruff check .
```

## Project layout

```
ingest/
  __init__.py
  __main__.py        → python -m ingest
  cli.py             → typer commands (run, pipeline, list-sources)
  config.py          → loads .env, exposes typed settings
  models.py          → SourceRecord, FetchResult (pydantic)
  llm.py             → thin Anthropic Messages wrapper (structured output)
  validate.py        → deterministic filter (bbox, empty names, country)
  dedupe.py          → deterministic clusterer (haversine + name Jaccard)
  pipeline.py        → orchestration: fetch -> validate -> dedupe -> normalize -> write
  sources/
    __init__.py      → REGISTRY of sources
    base.py          → Source protocol
    osm.py           → Overpass API fetcher
  agents/
    normalizer.py    → merges a Cluster -> NormalizedCourt (deterministic + LLM)
    (future: research.py using claude-agent-sdk)
  writer/
    supabase.py      → truncate-and-reload writer via psycopg
tests/               → pytest suite
data/                → output snapshots (gitignored)
```

## When we use which SDK

- **`anthropic`** (Messages API, one-shot): Normalizer and any other "input → structured JSON" task. Cheap, fast, deterministic at the call site.
- **`claude-agent-sdk`** (full agent loop, tool use): planned for the research agent (read web pages, scrape PDFs, write reports) and the ops/quality-audit agent. Not used yet — the dependency is declared so the scaffolding is ready.

## Next steps

1. Add `google_places` source once the Google Cloud key is available.
2. Add the normalizer agent (Claude Haiku) to merge records from multiple sources.
3. Add a `db write` command that bulk-upserts into Supabase via the schema in `packages/db/schema.sql`.
