"""Command-line entry point: `python -m ingest run --source osm`."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from ingest import sources

app = typer.Typer(add_completion=False, help="padel-atlas-de ingest pipeline")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@app.command()
def run(
    source: str = typer.Option(..., "--source", "-s", help="Source name (e.g. 'osm')."),
    out_dir: Path = typer.Option(DATA_DIR, "--out-dir", "-o", help="Where to write the JSON snapshot."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch one source and write the raw snapshot as JSON."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    fetcher = sources.get(source)
    result = fetcher.fetch()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"courts_{source}.json"
    out_path.write_text(result.model_dump_json(indent=2))
    typer.echo(f"wrote {result.count} records -> {out_path}")


@app.command()
def list_sources() -> None:
    """List available sources."""
    for name in sorted(sources.REGISTRY):
        typer.echo(name)


if __name__ == "__main__":
    app()
