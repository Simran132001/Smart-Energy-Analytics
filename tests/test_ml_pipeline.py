"""Feature engineering, model loading, prediction and anomaly detection tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tests.conftest import requires_gold, requires_model

from src.ml.anomaly_detection import detect, zscore_anomalies
from src.ml.evaluate import regression_metrics
from src.ml.feature_engineering import (
    add_lag_features,
    add_time_features,
    build_feature_matrix,
    time_series_split,
)


def test_regression_metrics_are_consistent():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    metrics = regression_metrics(y_true, y_true)
    assert metrics["mae"] == 0
    assert metrics["rmse"] == 0
    assert metrics["r2"] == 1

    metrics = regression_metrics(y_true, y_true + 1)
    assert metrics["mae"] == pytest.approx(1.0)
    assert metrics["rmse"] == pytest.approx(1.0)


def test_time_features_are_cyclical():
    df = pd.DataFrame({"hour": [0, 6, 12], "month": [1, 6, 12], "day_of_week": [1, 3, 7]})
    out = add_time_features(df)
    assert out["hour_sin"].between(-1, 1).all()
    assert out["month_cos"].between(-1, 1).all()


@requires_gold
def test_lag_features_are_shifted(sample_readings):
    out = add_lag_features(sample_readings)
    assert "lag_1h" in out.columns
    non_null = out.dropna(subset=["lag_1h"])
    assert np.allclose(
        non_null["lag_1h"].to_numpy()[1:],
        non_null["energy_consumption"].to_numpy()[:-1],
        atol=1e-6,
    )


@requires_gold
def test_time_series_split_is_chronological(sample_readings):
    X, y, metadata = build_feature_matrix(sample_readings)
    X_train, X_test, y_train, y_test, test_meta = time_series_split(X, y, metadata, 0.25)
    assert len(X_train) + len(X_test) == len(X)
    assert test_meta["timestamp"].min() >= metadata["timestamp"].min()
    assert len(y_train) == len(X_train)


@requires_model
@requires_gold
def test_model_loads_and_predicts(sample_readings):
    from src.ml.predict import load_model, predict_frame

    artifact = load_model()
    assert artifact["model_name"] in {"LinearRegression", "RandomForest", "GradientBoosting"}
    assert artifact["feature_columns"]

    predictions = predict_frame(sample_readings, artifact)
    assert len(predictions) > 0
    assert predictions["predicted_consumption"].notna().all()
    assert (predictions["predicted_consumption"] > 0).mean() > 0.9


@requires_model
@requires_gold
def test_predict_single_rejects_unknown_meter():
    from src.ml.predict import predict_single

    with pytest.raises(ValueError):
        predict_single(
            {"timestamp": "2024-01-01 10:00:00", "meter_id": "MTR-999", "temperature": 10, "humidity": 50}
        )


def test_zscore_flags_injected_spike():
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=240, freq="h"),
            "meter_id": "MTR-001",
            "hour": np.tile(np.arange(24), 10),
            "energy_consumption": rng.normal(3.0, 0.15, 240),
        }
    )
    frame.loc[100, "energy_consumption"] = 30.0
    result = zscore_anomalies(frame, threshold=3.0)
    assert result.loc[100, "anomaly_flag"] == 1
    assert result.loc[100, "anomaly_type"] in {"sudden_spike", "high_consumption"}
    assert result["anomaly_flag"].sum() < 20


@requires_gold
def test_detect_returns_both_methods(sample_readings):
    result = detect(sample_readings)
    assert set(result["detection_method"]) == {"robust_zscore", "isolation_forest"}
    assert result["anomaly_severity"].isin({"none", "low", "medium", "high"}).all()
