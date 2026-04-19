"""Command-line entry point for the ingest package."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from ingest import sources
from ingest.pipeline import run_pipeline

app = typer.Typer(add_completion=False, help="padel-atlas-de ingest pipeline")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@app.command()
def run(
    source: str = typer.Option(..., "--source", "-s", help="Source name (e.g. 'osm')."),
    out_dir: Path = typer.Option(DATA_DIR, "--out-dir", "-o", help="Where to write the JSON snapshot."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch one source and write the raw snapshot as JSON."""
    _configure_logging(verbose)
    fetcher = sources.get(source)
    result = fetcher.fetch()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"courts_{source}.json"
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"wrote {result.count} records -> {out_path}")


@app.command()
def pipeline(
    sources_opt: list[str] = typer.Option(
        ["osm"], "--source", "-s", help="Sources to include. Repeat for multiple."
    ),
    out_dir: Path = typer.Option(DATA_DIR, "--out-dir", "-o"),
    normalize: bool = typer.Option(
        False,
        "--normalize/--no-normalize",
        help="Call the LLM normalizer for ambiguous clusters (requires ANTHROPIC_API_KEY).",
    ),
    write: bool = typer.Option(
        False,
        "--write/--no-write",
        help="Write results to Supabase (requires SUPABASE_DB_URL).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run fetch -> validate -> dedupe (-> normalize -> write) end-to-end."""
    _configure_logging(verbose)
    report = run_pipeline(sources_opt, use_llm=normalize, write_to_db=write)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "pipeline_summary.json"
    clusters_path = out_dir / "courts_clustered.json"

    summary_path.write_text(json.dumps(report.summary(), indent=2), encoding="utf-8")
    clusters_payload = [
        {
            "normalized": nc.model_dump(mode="json"),
            "source_types": sorted(c.source_types),
            "record_count": len(c.records),
        }
        for c, nc in zip(report.clusters, report.normalized, strict=True)
    ]
    clusters_path.write_text(
        json.dumps(clusters_payload, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )

    typer.echo(json.dumps(report.summary(), indent=2))
    typer.echo(f"wrote summary -> {summary_path}")
    typer.echo(f"wrote clusters -> {clusters_path}")


@app.command("list-sources")
def list_sources() -> None:
    """List available sources."""
    for name in sorted(sources.REGISTRY):
        typer.echo(name)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    app()
