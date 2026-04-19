"""Runtime configuration: loads .env once, exposes typed settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE, override=False)


class Settings(BaseModel):
    supabase_db_url: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5"
    google_places_api_key: str | None = None


@lru_cache
def settings() -> Settings:
    return Settings(
        supabase_db_url=os.environ.get("SUPABASE_DB_URL") or None,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        llm_model=os.environ.get("LLM_MODEL") or "claude-haiku-4-5",
        google_places_api_key=os.environ.get("GOOGLE_PLACES_API_KEY") or None,
    )


def require(attr: str) -> str:
    value = getattr(settings(), attr)
    if not value:
        raise RuntimeError(
            f"Missing required config: {attr}. "
            f"Copy packages/ingest/.env.example to .env and fill it in."
        )
    return value
