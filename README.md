# padel-atlas-de

Data platform & Deutschlandkarte der Padel-Courts — plus Whitespace-Analyse für Standortchancen.

> **Status:** v0 / Woche 1. Aktuell wird der Daten-Ingest aufgebaut.
> Frontend-Karte folgt in Woche 2.

## Was macht dieses Projekt?

1. **Sammelt** alle Padel-Courts in Deutschland aus mehreren Quellen (OpenStreetMap, Google Places, Playtomic, Matchi, DPV, …).
2. **Normalisiert** sie mit Agenten (Claude) zu einem sauberen Datenmodell.
3. **Visualisiert** sie auf einer Deutschlandkarte.
4. **Identifiziert** Regionen mit hoher Nachfrage und niedrigem Angebot (Whitespace-Analyse).

## Repo-Struktur

```
apps/
  web/              → Next.js Frontend (folgt in Woche 2)
packages/
  db/               → Supabase/PostGIS Schema und Migrationen
  ingest/           → Python — Scraper & Claude-Agenten für Court-Daten
docs/               → Architektur, Entscheidungen, Onboarding
```

## Tech-Stack

- **Datenbank:** Supabase (Postgres + PostGIS)
- **Ingest:** Python 3.11+, httpx, Pydantic, Claude Agent SDK
- **Frontend:** Next.js 15 + MapLibre GL + Tailwind (ab Woche 2)
- **Hosting:** Vercel (Web) + Supabase (DB) + GitHub Actions (Ingest-Cron)

## Schnellstart (lokal, für später wenn du am Laptop bist)

```bash
# Ingest ausführen (OSM, keine API-Keys nötig)
cd packages/ingest
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m ingest run --source osm
# → schreibt ./data/courts_osm.json
```

Details und Onboarding-Guide: [`docs/onboarding.md`](docs/onboarding.md)
