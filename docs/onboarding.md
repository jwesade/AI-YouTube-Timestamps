# Onboarding — padel-atlas-de

Kurzanleitung für Anfänger. Du brauchst das **erst**, sobald du an deinem Laptop sitzt.

## 1. Accounts (ca. 15 Min)

Lege dir diese kostenlosen Accounts an und schicke mir die Namen (keine Passwörter!):

- [ ] **GitHub** — hast du schon
- [ ] **Supabase** (https://supabase.com) → neues Projekt "padel-atlas-de" anlegen, Region `eu-central-1`
- [ ] **Vercel** (https://vercel.com) → mit GitHub verbinden, kein eigenes Projekt anlegen (mache ich)
- [ ] **Anthropic Console** (https://console.anthropic.com) → $20 aufladen (reicht monatelang)
- [ ] **Google Cloud** (erst wenn wir Places API anschließen, nicht jetzt)

## 2. Laptop-Setup (ca. 30 Min, einmalig)

### macOS
```bash
# Homebrew (falls noch nicht installiert)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install git node python@3.11
```

### Windows
- Git for Windows: https://git-scm.com/download/win
- Node.js LTS: https://nodejs.org
- Python 3.11: https://www.python.org/downloads/
- Alles mit Standardeinstellungen installieren.

### Editor
- **Cursor** (https://cursor.com) — VS Code mit KI-Integration. Empfohlen.

## 3. Repo klonen

```bash
git clone https://github.com/jwesade/ai-youtube-timestamps padel-atlas-de
cd padel-atlas-de
```

## 4. Ingest lokal ausführen

```bash
cd packages/ingest
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
python -m ingest run --source osm
```

Erwartetes Ergebnis: `data/courts_osm.json` mit ~50–200 Einträgen. Öffne die Datei — das sind deine ersten echten Padel-Court-Daten.

## 5. Datenbank aufsetzen

In Supabase → **SQL Editor** → Inhalt von `packages/db/schema.sql` einfügen → **Run**.

Von **Settings → API** holst du:
- `Project URL` → `SUPABASE_URL`
- `service_role key` (geheim!) → `SUPABASE_SERVICE_ROLE_KEY`

Diese trägst du in `packages/ingest/.env` ein (kopiere `.env.example`).

## Nächste Schritte

Wenn das alles läuft, bauen wir:
1. Google Places Source Fetcher
2. Normalizer Agent (Claude Haiku) zum Zusammenführen
3. Next.js Frontend mit Deutschlandkarte

Frage mich jederzeit bei Stolpersteinen — ich kenne jeden Schritt.
