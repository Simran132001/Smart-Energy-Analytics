"""Load the Gold datasets into the PostgreSQL warehouse (idempotent)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.db.postgres import get_connection, get_engine, schema
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_SCRIPT = PROJECT_ROOT / "sql" / "postgres" / "01_schema.sql"
VIEWS_SCRIPT = PROJECT_ROOT / "sql" / "postgres" / "02_analytics_views.sql"

# gold dataset -> (target table, column renames, truncate-before-load)
LOAD_PLAN = {
    "dim_meter": ("dim_meter", {}, True),
    "dim_date": ("dim_date", {"date": "date_key"}, True),
    "meter_consumption": ("fact_meter_consumption", {}, True),
    "hourly_consumption": ("fact_hourly_consumption", {"date": "date_key"}, True),
    "daily_consumption": ("fact_daily_consumption", {"date": "date_key"}, True),
    "monthly_consumption": ("fact_monthly_consumption", {}, True),
    "peak_offpeak_consumption": ("fact_peak_offpeak", {"date": "date_key"}, True),
    "weather_energy": ("fact_weather_energy", {"date": "date_key"}, True),
    "energy_summary": ("energy_summary", {}, True),
}

TABLE_COLUMNS = {
    "dim_meter": [
        "meter_id", "meter_type", "region", "installation_date", "rated_voltage",
        "base_load_kwh", "avg_consumption", "total_consumption",
    ],
    "dim_date": [
        "date_key", "year", "quarter", "month", "month_name", "day", "day_of_week",
        "day_name", "weekend_flag", "season",
    ],
}


def apply_schema() -> None:
    with get_engine().begin() as connection:
        connection.execute(text(SCHEMA_SCRIPT.read_text(encoding="utf-8")))
    logger.info("Applied warehouse schema")


def apply_views() -> None:
    if VIEWS_SCRIPT.exists():
        with get_engine().begin() as connection:
            connection.execute(text(VIEWS_SCRIPT.read_text(encoding="utf-8")))
        logger.info("Applied analytics views")


def _read_gold(gold_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_parquet(gold_dir / f"{name}.parquet")


def load_table(df: pd.DataFrame, table: str, truncate: bool) -> int:
    if table in TABLE_COLUMNS:
        df = df[[column for column in TABLE_COLUMNS[table] if column in df.columns]]
    with get_connection() as connection:
        if truncate:
            connection.execute(text(f"TRUNCATE TABLE {schema()}.{table} CASCADE"))
    df.to_sql(table, get_engine(), schema=schema(), if_exists="append", index=False, chunksize=5000)
    logger.info("Loaded %d rows into %s", len(df), table)
    return len(df)


def run(gold_dir: str | Path | None = None) -> dict:
    config = load_config()
    directory = Path(gold_dir) if gold_dir else PROJECT_ROOT / config["paths"]["gold"]

    apply_schema()
    counts: dict[str, int] = {}
    # Dimensions first so the fact foreign keys resolve.
    for dataset, (table, renames, truncate) in LOAD_PLAN.items():
        path = directory / f"{dataset}.parquet"
        if not path.exists():
            logger.warning("Gold dataset %s missing, skipping", dataset)
            continue
        df = _read_gold(directory, dataset).rename(columns=renames)
        counts[table] = load_table(df, table, truncate)
    apply_views()
    logger.info("PostgreSQL load complete: %s", counts)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Gold datasets into PostgreSQL")
    parser.add_argument("--gold-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.gold_dir), indent=2))


if __name__ == "__main__":
    main()
