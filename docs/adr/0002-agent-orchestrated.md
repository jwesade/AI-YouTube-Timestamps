# ADR 0002 — Agent-orchestrierte, nicht „Agent-alles"-Architektur

**Status:** Akzeptiert · **Datum:** 2026-04-18

## Kontext

Die ursprüngliche Vision ist „alles agentisch": jeder Schritt — Scraping, Normalisierung, Geocoding, Storage — wird von einem LLM-Agenten bedient. Das ist verlockend, aber:

1. **LLMs sind teuer und langsam** für Routineaufgaben (HTTP-Calls, SQL-Writes). Ein Agent, der 1.000 OSM-Knoten in eine Tabelle überträgt, kostet unnötig.
2. **LLMs sind probabilistisch.** Das ist eine Stärke bei *unscharfen* Problemen (ist „Padel Base Berlin" und „PadelBase Berlin" derselbe Ort?) und eine Schwäche bei *deterministischen* Problemen (POST an eine Datenbank).
3. **Debugging:** Fehler in deterministischem Code lassen sich mit Tests reproduzieren. Fehler in Agent-Prompts nicht.

## Entscheidung

**Agenten orchestrieren die Pipeline, deterministische Tools erledigen die Arbeit.**

Aufgabenteilung:

| Aufgabe                         | Besitzer (v0)        | Später                         |
|---------------------------------|----------------------|--------------------------------|
| HTTP-Requests / Scrapen         | Deterministisch (httpx) | Deterministisch               |
| JSON/HTML → strukturiertes Dict | Deterministisch (Parser) | Agent wenn HTML irregulär     |
| Validierung (bbox, leere Namen) | Deterministisch      | Deterministisch                |
| Duplikate erkennen (einfach)    | Deterministisch (haversine + Jaccard) | Agent für unscharfe Fälle |
| Name normalisieren              | Agent (Claude Haiku) | Agent                          |
| Datenbank-Writes                | Deterministisch (psycopg) | Deterministisch            |
| Qualitätssicherung (Stichproben) | Agent (Claude Sonnet) | Agent                         |

Agenten werden mit dem **Claude Agent SDK** gebaut, bekommen deterministische Tools (Python-Funktionen) an die Hand und geben strukturierte Outputs zurück.

## Konsequenzen

**Gut:**
- Kosten bleiben im ein- bis zweistelligen Euro-Bereich pro Monat statt hunderte.
- Pipeline läuft schnell: deterministische Schritte sind in Millisekunden durch, Agent-Schritte nur dort wo nötig.
- Tests sind einfacher — wir testen Agenten separat von der Pipeline.

**Zu beachten:**
- Klare Grenzen nötig: *was* ist Agent-Aufgabe, *was* deterministisch. Wir dokumentieren das pro Modul.
- Wir evaluieren regelmäßig, ob eine deterministische Regel einen Agenten einsparen kann (z. B. wenn wir den Rewrite per Regex hinbekommen).

**Upgrade-Pfad zu „wirklich alles agentisch":** Wenn Modelle billiger und zuverlässiger werden, können wir einzelne deterministische Schritte durch Agenten ersetzen. Die Modulgrenzen machen das zu einem lokalen, low-risk-Refactor.
