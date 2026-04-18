from ingest.sources.base import Source
from ingest.sources.osm import OSMSource

REGISTRY: dict[str, type[Source]] = {
    "osm": OSMSource,
}


def get(name: str) -> Source:
    try:
        return REGISTRY[name]()
    except KeyError as exc:
        available = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown source '{name}'. available: {available}") from exc
