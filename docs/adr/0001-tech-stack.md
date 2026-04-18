# ADR 0001 — Tech-Stack: Supabase + Next.js + Vercel

**Status:** Akzeptiert · **Datum:** 2026-04-18

## Kontext

padel-atlas-de ist im Kern ein Geo-Produkt: „zeige alle Padel-Courts in Deutschland auf einer Karte; finde Regionen mit hoher Nachfrage und geringem Angebot". Das stellt drei Anforderungen:

1. **Geo-Queries** (Umkreissuche, Bounding-Box, Dichte-Heatmaps pro Kreis/PLZ).
2. **Öffentliche Webseite**, SEO-freundlich, mit interaktiver Karte.
3. **Batch-Ingest** alle paar Stunden/Tage, orchestrierbar per CI/Cron.

Die Gründerin ist nicht-technisch und braucht einen Stack, der bei einer kleinen Projektgröße **kostenlos** (oder fast kostenlos) anfängt, aber **auf Enterprise-Niveau skaliert**, ohne später migrieren zu müssen.

## Entscheidung

- **Datenbank:** Supabase (Postgres 15 + PostGIS). Kostenloser Tier reicht bis ~500 MB Datenbank und 50k monatliche Users. Hosted, mit Auth, Row-Level-Security, Realtime, Dashboard.
- **Frontend:** Next.js 15 (App Router) + MapLibre GL JS (Open-Source-Karten, keine Google-Abhängigkeit) + Tailwind.
- **Hosting:** Vercel für das Next.js-Frontend. Preview-URL pro Pull Request gratis.
- **Ingest:** Python 3.11, als separates Paket im Monorepo. Läuft via GitHub Actions (cron) oder lokal. Schreibt direkt in Supabase über `psycopg` oder den Supabase-Python-Client.

## Alternativen, die wir verworfen haben

- **Firebase + React** (aus dem ursprünglichen Template): Firestore ist für Geo-Queries schwach (Geohash-Hack nötig), kein echtes Postgres, schlechtere Integration mit Datentools (dbt, BI). Die „Ersparnis" an Setup-Komplexität wiegt den spätere Migrationsaufwand nicht auf.
- **Self-hosted Postgres + Terraform**: maximale Kontrolle, aber Betriebslast für ein Ein-Personen-Projekt zu hoch.
- **Google Maps statt MapLibre**: schöner, aber teuer (Preis pro Map-Load) und lockt uns in ein proprietäres Ökosystem.

## Konsequenzen

**Gut:**
- PostGIS macht Whitespace-Analysen trivial (`ST_Distance`, `ST_Within` auf GeoJSON-Landkreisen).
- Vercel + GitHub Actions → CI/CD ohne eigene Infrastruktur.
- Einfache lokale Entwicklung: `docker compose up` bzw. Supabase CLI reicht.

**Zu beachten:**
- Supabase-Free-Tier hat Pausierungsregeln bei Inaktivität; wir müssen das monitoren.
- MapLibre braucht ein Tile-Provider (z. B. MapTiler mit freiem Kontingent) — nicht ganz „null Konfig".
- Migration weg von Vercel ginge — die Next.js-Codebasis ist portabel zu z. B. Cloudflare Pages.
