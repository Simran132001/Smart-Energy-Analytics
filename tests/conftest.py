"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def _database_available() -> bool:
    try:
        from src.db.postgres import healthcheck

        return healthcheck()
    except Exception:  # noqa: BLE001
        return False


requires_gold = pytest.mark.skipif(
    not (GOLD_DIR / "powerbi_fact_consumption.parquet").exists(),
    reason="Gold datasets not built - run scripts/run_pipeline.py",
)

requires_db = pytest.mark.skipif(not _database_available(), reason="PostgreSQL not reachable")

requires_model = pytest.mark.skipif(
    not (PROJECT_ROOT / "models" / "best_model.joblib").exists(),
    reason="Model artifact not trained",
)


@pytest.fixture(scope="session")
def gold_dir() -> Path:
    return GOLD_DIR


@pytest.fixture(scope="session")
def ml_features() -> pd.DataFrame:
    return pd.read_parquet(GOLD_DIR / "ml_features.parquet")


@pytest.fixture(scope="session")
def sample_readings() -> pd.DataFrame:
    df = pd.read_parquet(GOLD_DIR / "ml_features.parquet")
    return df[df["meter_id"] == df["meter_id"].iloc[0]].tail(500).reset_index(drop=True)


@pytest.fixture(scope="session")
def spark():
    pytest.importorskip("pyspark")
    from src.utils.spark_session import get_spark

    session = get_spark("pytest")
    yield session


@pytest.fixture()
def api_client():
    os.environ.setdefault("FLASK_ENV", "testing")
    from src.api.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client
