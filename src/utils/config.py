"""Configuration loading utilities."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

load_dotenv(PROJECT_ROOT / ".env")


@lru_cache(maxsize=4)
def load_config(path: str | os.PathLike[str] | None = None) -> Dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_path(relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def data_path(layer: str) -> Path:
    config = load_config()
    return resolve_path(config["paths"][layer])


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise KeyError(f"Missing required environment variable: {name}")
    return value
