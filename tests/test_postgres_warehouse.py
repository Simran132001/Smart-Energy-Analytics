"""PostgreSQL warehouse tests."""
from __future__ import annotations

import pytest

from tests.conftest import requires_db

from src.db.postgres import read_sql, table_exists

TABLES = [
    "dim_meter",
    "dim_date",
    "fact_hourly_consumption",
    "fact_daily_consumption",
    "fact_monthly_consumption",
    "fact_meter_consumption",
    "fact_peak_offpeak",
    "fact_weather_energy",
    "fact_predictions",
    "fact_anomalies",
    "energy_summary",
]

VIEWS = [
    "vw_energy_summary",
    "vw_daily_trend",
    "vw_monthly_trend",
    "vw_hourly_pattern",
    "vw_meter_ranking",
    "vw_top_meters",
    "vw_peak_offpeak",
    "vw_weekday_weekend",
    "vw_seasonal_consumption",
    "vw_weather_impact",
    "vw_anomaly_counts",
    "vw_anomaly_by_meter",
    "vw_prediction_accuracy",
    "vw_actual_vs_predicted",
]


@requires_db
@pytest.mark.parametrize("table", TABLES)
def test_tables_exist(table):
    assert table_exists(table)


@requires_db
@pytest.mark.parametrize("view", VIEWS)
def test_views_are_queryable(view):
    read_sql(f"SELECT * FROM {view} LIMIT 1")


@requires_db
def test_facts_are_populated():
    counts = read_sql(
        "SELECT (SELECT COUNT(*) FROM fact_daily_consumption) AS daily, "
        "(SELECT COUNT(*) FROM dim_meter) AS meters, "
        "(SELECT COUNT(*) FROM fact_predictions) AS predictions, "
        "(SELECT COUNT(*) FROM fact_anomalies) AS anomalies"
    ).iloc[0]
    assert counts["daily"] > 0
    assert counts["meters"] > 0
    assert counts["predictions"] > 0
    assert counts["anomalies"] > 0


@requires_db
def test_referential_integrity_of_facts():
    orphans = read_sql(
        "SELECT COUNT(*) AS orphans FROM fact_daily_consumption f "
        "LEFT JOIN dim_meter m ON f.meter_id = m.meter_id WHERE m.meter_id IS NULL"
    ).iloc[0]["orphans"]
    assert orphans == 0


@requires_db
def test_meter_ranking_is_dense_and_ordered():
    ranking = read_sql("SELECT meter_id, consumption_rank, total_consumption FROM vw_meter_ranking")
    assert list(ranking["consumption_rank"]) == list(range(1, len(ranking) + 1))
    assert ranking["total_consumption"].is_monotonic_decreasing
