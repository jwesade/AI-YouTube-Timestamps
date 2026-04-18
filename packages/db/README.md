# packages/db

Postgres/PostGIS schema for padel-atlas-de.

## Setup in Supabase

1. Create a new Supabase project at https://supabase.com/dashboard.
2. Open the **SQL Editor**.
3. Paste the contents of [`schema.sql`](schema.sql) and run it.
4. Grab the project URL and `anon` + `service_role` keys from **Settings → API**.
5. Put them into `packages/ingest/.env` (see `.env.example` there).

## Tables

- **`courts`** — one row per physical padel location (club / venue).
- **`sources`** — one row per external source that reported a given court. Multiple sources can point to the same court (e.g. OSM + Google Places + Playtomic).
- **`operators`** — optional, normalised operator names (e.g. "Padel Base", "Tennispoint").

## Why two tables for courts and sources?

We aggregate the same venue from multiple scrapers. Storing the raw source record separately lets us:
- Re-run the de-duplication / normalisation logic without losing provenance.
- Show "this court is confirmed by 3 sources" as a confidence signal.
- Cite sources in the UI ("Daten von OSM, Google, Playtomic").
