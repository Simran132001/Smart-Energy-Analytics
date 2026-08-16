"""Gold layer / Power BI readiness tests."""
from __future__ import annotations

import pandas as pd
import pytest

from tests.conftest import requires_gold

from powerbi.generate_powerbi_assets import REQUIRED_DATASETS


@requires_gold
@pytest.mark.parametrize("dataset", REQUIRED_DATASETS)
def test_gold_files_exist_in_both_formats(gold_dir, dataset):
    assert (gold_dir / f"{dataset}.parquet").exists()
    assert (gold_dir / f"{dataset}.csv").exists()


@requires_gold
def test_powerbi_fact_is_clean_and_typed(gold_dir):
    fact = pd.read_parquet(gold_dir / "powerbi_fact_consumption.parquet")

    assert not fact.duplicated(subset=["date", "hour", "meter_id"]).any()
    assert pd.api.types.is_datetime64_any_dtype(fact["date"])
    assert pd.api.types.is_numeric_dtype(fact["total_consumption"])
    assert fact["total_consumption"].notna().all()
    assert fact["anomaly_flag"].isin([0, 1]).all()

    required = {
        "date", "hour", "meter_id", "total_consumption", "avg_consumption", "max_consumption",
        "min_consumption", "temperature", "humidity", "weather_condition", "season",
        "weekend_flag", "peak_hour_flag", "anomaly_flag", "anomaly_type", "anomaly_severity",
        "predicted_consumption", "prediction_error",
    }
    assert required.issubset(set(fact.columns))


@requires_gold
def test_prediction_dataset_has_error_columns(gold_dir):
    predictions = pd.read_parquet(gold_dir / "predictions.parquet")
    assert {"timestamp", "meter_id", "actual_consumption", "predicted_consumption",
            "prediction_error", "model_name"}.issubset(predictions.columns)
    assert predictions["predicted_consumption"].notna().all()


@requires_gold
def test_anomaly_dataset_only_contains_anomalies(gold_dir):
    anomalies = pd.read_parquet(gold_dir / "anomalies.parquet")
    assert (anomalies["anomaly_flag"] == 1).all()
    assert anomalies["anomaly_severity"].isin({"low", "medium", "high"}).all()


@requires_gold
def test_dimensions_have_unique_keys(gold_dir):
    dim_date = pd.read_parquet(gold_dir / "dim_date.parquet")
    dim_meter = pd.read_parquet(gold_dir / "dim_meter.parquet")
    assert dim_date["date"].is_unique
    assert dim_meter["meter_id"].is_unique


@requires_gold
def test_fact_meter_keys_exist_in_dimension(gold_dir):
    fact = pd.read_parquet(gold_dir / "powerbi_fact_consumption.parquet")
    dim_meter = pd.read_parquet(gold_dir / "dim_meter.parquet")
    assert set(fact["meter_id"]).issubset(set(dim_meter["meter_id"]))
