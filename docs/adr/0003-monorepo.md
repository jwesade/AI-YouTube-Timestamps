# ADR 0003 — Monorepo-Layout

**Status:** Akzeptiert · **Datum:** 2026-04-18

## Kontext

Das Projekt hat von Anfang an mehrere Laufzeiten: ein Python-Ingest, ein Next.js-Frontend, ein DB-Schema. Wir wollen sie **gemeinsam versionieren**, damit ein Schema-Change und die passenden Frontend-/Ingest-Änderungen im selben Commit landen.

## Entscheidung

Single Repository mit folgender Struktur:

```
apps/
  web/              → Next.js Frontend (Node.js)
packages/
  db/               → SQL Schema + Migrationen (language-agnostisch)
  ingest/           → Python Paket (eigenes pyproject.toml)
docs/
  adr/              → Architecture Decision Records
  onboarding.md     → Einsteigerleitfaden
.github/
  workflows/        → CI (pro Projekt ein Job)
```

**Konventionen:**
- Jedes Verzeichnis in `apps/` oder `packages/` hat ein eigenes README.
- CI-Jobs sind pro Paket isoliert (`working-directory:` in GitHub Actions).
- Keine „Supporting-Libraries"-Hölle: wenn Python und TypeScript denselben Typ brauchen, generieren wir ihn aus dem SQL-Schema, nicht aus einer geteilten Library.

## Alternativen

- **Mehrere Repos (polyrepo):** Mehr Overhead bei Schema-Änderungen (zwei Pull Requests koordinieren), keine atomaren Cross-Cutting-Commits. Verworfen.
- **Yarn/npm-Workspaces / Turborepo:** Overkill für v0. Wenn wir JavaScript-Pakete teilen wollen, können wir Turborepo später überlagern — ohne das Repo-Layout zu zerstören.
- **Nx / Bazel:** Gleiche Überlegung, zu schwer für den Anfang.

## Konsequenzen

**Gut:**
- Atomar: ein Commit ändert Schema + Ingest + Frontend konsistent.
- Einsteiger finden alles an einem Ort.
- CI kann selektiv laufen (nur Python-Tests wenn nur `packages/ingest/` geändert wurde — per `paths:` in der Workflow-Definition, wenn relevant).

**Zu beachten:**
- Das Repo wächst schneller. Wenn es unhandlich wird (> 100k Zeilen), splitten wir.
- Dependency-Upgrades müssen pro Paket laufen (Dependabot erledigt das automatisch — das richten wir später ein).
