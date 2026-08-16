"""Batch and single-record consumption prediction."""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

from src.db.postgres import get_connection, get_engine, schema
from src.ml.feature_engineering import build_feature_matrix, load_ml_features, time_series_split
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import write_gold
from src.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_INPUT_FIELDS = ("timestamp", "meter_id", "temperature", "humidity")


@lru_cache(maxsize=1)
def load_model(path: str | None = None) -> dict[str, Any]:
    config = load_config()
    model_file = Path(path) if path else PROJECT_ROOT / config["paths"]["models"] / "best_model.joblib"
    if not model_file.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_file}. Run src.ml.train first.")
    artifact = joblib.load(model_file)
    logger.info("Loaded model %s v%s", artifact["model_name"], artifact["model_version"])
    return artifact


def _align(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    return frame.reindex(columns=feature_columns, fill_value=0.0).astype(float)


def predict_frame(df: pd.DataFrame, artifact: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Predict for a raw feature frame (must contain the base reading columns)."""
    artifact = artifact or load_model()
    X, _, metadata = build_feature_matrix(df)
    predictions = artifact["model"].predict(_align(X, artifact["feature_columns"]))
    result = metadata.copy()
    result["predicted_consumption"] = np.round(predictions, 4)
    result["model_name"] = artifact["model_name"]
    result["model_version"] = artifact["model_version"]
    return result


def predict_single(payload: Mapping[str, Any], artifact: Mapping[str, Any] | None = None) -> dict:
    """Predict one reading; missing lag features fall back to recent history."""
    artifact = artifact or load_model()
    missing = [field for field in REQUIRED_INPUT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    history = load_ml_features()
    meter_history = history[history["meter_id"] == payload["meter_id"]]
    if meter_history.empty:
        raise ValueError(f"Unknown meter_id: {payload['meter_id']}")

    template = meter_history.iloc[-1].to_dict()
    template.update({k: v for k, v in payload.items() if k in template or k in REQUIRED_INPUT_FIELDS})
    template["timestamp"] = pd.to_datetime(payload["timestamp"])
    template["hour"] = template["timestamp"].hour
    template["day"] = template["timestamp"].day
    template["month"] = template["timestamp"].month
    template["year"] = template["timestamp"].year
    template["day_of_week"] = int(template["timestamp"].dayofweek) + 1
    template["weekend_flag"] = int(template["timestamp"].dayofweek >= 5)
    template["peak_hour_flag"] = int(template["hour"] in list(range(7, 11)) + list(range(17, 22)))

    frame = pd.concat(
        [meter_history.tail(48), pd.DataFrame([template])], ignore_index=True
    )
    predicted = predict_frame(frame, artifact).iloc[-1]
    return {
        "timestamp": str(predicted["timestamp"]),
        "meter_id": predicted["meter_id"],
        "predicted_consumption": float(predicted["predicted_consumption"]),
        "model_name": artifact["model_name"],
        "model_version": artifact["model_version"],
    }


def build_prediction_dataset() -> pd.DataFrame:
    """Score the chronological hold-out window and compute error columns."""
    artifact = load_model()
    X, y, metadata = build_feature_matrix(load_ml_features())
    _, X_test, _, y_test, test_meta = time_series_split(X, y, metadata, load_config()["ml"]["test_size"])
    predictions = artifact["model"].predict(_align(X_test, artifact["feature_columns"]))

    frame = test_meta.copy()
    frame["actual_consumption"] = np.round(y_test.to_numpy(), 4)
    frame["predicted_consumption"] = np.round(predictions, 4)
    frame["prediction_error"] = np.round(frame["predicted_consumption"] - frame["actual_consumption"], 4)
    frame["abs_percentage_error"] = np.round(
        100.0 * frame["prediction_error"].abs() / frame["actual_consumption"].replace(0, np.nan), 4
    ).fillna(0.0)
    frame["model_name"] = artifact["model_name"]
    frame["model_version"] = artifact["model_version"]
    return frame


def store_predictions(frame: pd.DataFrame) -> int:
    payload = frame.rename(columns={"timestamp": "reading_ts"})[
        [
            "reading_ts", "meter_id", "actual_consumption", "predicted_consumption",
            "prediction_error", "abs_percentage_error", "model_name", "model_version",
        ]
    ]
    with get_connection() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {schema()}.fact_predictions")
    payload.to_sql(
        "fact_predictions", get_engine(), schema=schema(), if_exists="append", index=False, chunksize=5000
    )
    logger.info("Stored %d predictions in PostgreSQL", len(payload))
    return len(payload)


def run() -> dict:
    config = load_config()
    frame = build_prediction_dataset()
    paths = write_gold(frame, PROJECT_ROOT / config["paths"]["gold"], "predictions")
    stored = store_predictions(frame)
    summary = {
        "rows": int(len(frame)),
        "stored_in_postgres": stored,
        "gold_files": paths,
        "mae": round(float(frame["prediction_error"].abs().mean()), 5),
        "mape": round(float(frame["abs_percentage_error"].mean()), 5),
    }
    logger.info("Prediction stage complete: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and persist predictions")
    parser.parse_args()
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
