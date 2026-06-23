"""Load settings.yaml + .env into one place."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")


@lru_cache
def settings() -> dict[str, Any]:
    path = ROOT / "config" / "settings.yaml"
    if not path.exists():
        raise FileNotFoundError(
            "config/settings.yaml not found. Copy config/settings.example.yaml "
            "to config/settings.yaml and edit it."
        )
    with path.open() as fh:
        return yaml.safe_load(fh)


def env(key: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val
