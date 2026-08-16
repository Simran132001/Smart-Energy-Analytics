"""PySpark transformation tests for the Silver and Gold stages."""
from __future__ import annotations

import datetime as dt

import pytest

pytest.importorskip("pyspark")

from src.etl.bronze_to_silver import clean, deduplicate, enrich  # noqa: E402
from src.etl.silver_to_gold import daily_consumption, meter_consumption  # noqa: E402
from src.utils.config import load_config  # noqa: E402


@pytest.fixture()
def bronze_df(spark):
    rows = [
        ("MTR-001", "residential", "North", dt.datetime(2023, 6, 1, 8), 2.5, 230.0, 11.0, 0.95,
         21.0, 55.0, "Clear", dt.datetime(2023, 6, 2), "csv"),
        # duplicate of the previous reading with a later ingestion timestamp
        ("MTR-001", "residential", "North", dt.datetime(2023, 6, 1, 8), 2.7, 230.0, 11.0, 0.95,
         21.0, 55.0, "Clear", dt.datetime(2023, 6, 3), "csv"),
        ("MTR-002", "commercial", "South", dt.datetime(2023, 6, 3, 19), 6.0, -5.0, 26.0, 0.92,
         31.0, 40.0, "clear ", dt.datetime(2023, 6, 4), "csv"),
        ("BAD-ID", "commercial", "South", dt.datetime(2023, 6, 3, 19), 6.0, 230.0, 26.0, 0.92,
         31.0, 40.0, "Clear", dt.datetime(2023, 6, 4), "csv"),
    ]
    columns = [
        "meter_id", "meter_type", "region", "timestamp", "energy_consumption", "voltage",
        "current", "power_factor", "temperature", "humidity", "weather_condition",
        "ingestion_ts", "source_system",
    ]
    return spark.createDataFrame(rows, columns)


def test_deduplicate_keeps_latest_ingestion(bronze_df):
    result = deduplicate(bronze_df).filter("meter_id = 'MTR-001'").collect()
    assert len(result) == 1
    assert result[0]["energy_consumption"] == 2.7


def test_clean_drops_invalid_meter_ids_and_repairs_voltage(bronze_df):
    cleaned = clean(deduplicate(bronze_df), load_config()["quality"])
    meter_ids = {row["meter_id"] for row in cleaned.collect()}
    assert "BAD-ID" not in meter_ids
    # The -5.0 voltage is invalid and imputed from the meter average, never kept as-is.
    assert all(row["voltage"] is None or row["voltage"] > 0 for row in cleaned.collect())


def test_enrich_adds_derived_columns(bronze_df):
    enriched = enrich(clean(deduplicate(bronze_df), load_config()["quality"]))
    for column in (
        "date", "year", "month", "day", "hour", "minute", "day_of_week",
        "weekend_flag", "peak_hour_flag", "season", "temperature_band", "tariff_period",
    ):
        assert column in enriched.columns

    row = enriched.filter("meter_id = 'MTR-001'").collect()[0]
    assert row["hour"] == 8
    assert row["peak_hour_flag"] == 1
    assert row["season"] == "Summer"
    assert row["weather_condition"] == "Clear"


def test_gold_aggregations(bronze_df):
    silver = enrich(clean(deduplicate(bronze_df), load_config()["quality"]))
    daily = daily_consumption(silver)
    assert daily.count() == 2
    assert "total_consumption" in daily.columns

    ranking = meter_consumption(silver).collect()
    assert [row["consumption_rank"] for row in ranking] == list(range(1, len(ranking) + 1))
