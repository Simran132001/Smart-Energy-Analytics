"""PostgreSQL connectivity helpers."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)
_ENGINE: Engine | None = None


def connection_url() -> str:
    return (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'energy_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'energy_pass')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'smart_energy')}"
    )


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(connection_url(), pool_pre_ping=True, future=True)
        logger.info("Created PostgreSQL engine for %s", os.getenv("POSTGRES_DB", "smart_energy"))
    return _ENGINE


def schema() -> str:
    return load_config()["postgres"]["schema"]


@contextmanager
def get_connection() -> Iterator:
    with get_engine().begin() as connection:
        connection.execute(text(f"SET search_path TO {schema()}, public"))
        yield connection


def execute_script(path: str) -> None:
    with open(path, "r", encoding="utf-8") as handle:
        sql = handle.read()
    with get_engine().begin() as connection:
        connection.execute(text(sql))
    logger.info("Applied SQL script %s", path)


def read_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    with get_connection() as connection:
        return pd.read_sql(text(query), connection, params=params or {})


def table_exists(table: str) -> bool:
    query = (
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = :table"
    )
    with get_engine().begin() as connection:
        return connection.execute(text(query), {"schema": schema(), "table": table}).first() is not None


def healthcheck() -> bool:
    try:
        with get_engine().begin() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health endpoint must not raise
        logger.warning("PostgreSQL healthcheck failed: %s", exc)
        return False
