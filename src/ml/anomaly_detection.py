"""Anomaly detection over the Silver/Gold consumption history.

Combines a per-meter, per-hour robust z-score (captures sudden spikes and
unusually low readings) with an IsolationForest on the multivariate reading
profile (captures abnormal meter behaviour).
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.db.postgres import get_connection, get_engine, schema
from src.ml.feature_engineering import load_ml_features
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import write_gold
from src.utils.logger import get_logger

logger = get_logger(__name__)

SEVERITY_BINS = [("high", 6.0), ("medium", 4.0), ("low", 0.0)]


def _severity(score: float) -> str:
    for label, threshold in SEVERITY_BINS:
        if abs(score) >= threshold:
            return label
    return "low"


def zscore_anomalies(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Robust z-score per meter and hour-of-day baseline."""
    grouped = df.groupby(["meter_id", "hour"])["energy_consumption"]
    median = grouped.transform("median")
    mad = grouped.transform(lambda s: (s - s.median()).abs().median())
    scale = (1.4826 * mad).replace(0, np.nan)
    score = ((df["energy_consumption"] - median) / scale).fillna(0.0)

    out = df[["timestamp", "meter_id", "energy_consumption"]].copy()
    out["anomaly_score"] = np.round(score, 4)
    out["anomaly_flag"] = (score.abs() >= threshold).astype(int)
    out["anomaly_type"] = np.select(
        [
            (out["anomaly_flag"] == 1) & (score > 0) & (score.abs() >= 2 * threshold),
            (out["anomaly_flag"] == 1) & (score > 0),
            (out["anomaly_flag"] == 1) & (score < 0),
        ],
        ["sudden_spike", "high_consumption", "low_consumption"],
        default="normal",
    )
    out["detection_method"] = "robust_zscore"
    return out


def isolation_forest_anomalies(df: pd.DataFrame, contamination: float, random_state: int) -> pd.DataFrame:
    features = ["energy_consumption", "voltage", "current", "power_factor", "temperature", "humidity"]
    matrix = df[features].fillna(df[features].median())
    model = IsolationForest(
        n_estimators=150, contamination=contamination, random_state=random_state, n_jobs=-1
    )
    labels = model.fit_predict(matrix)
    scores = model.score_samples(matrix)

    out = df[["timestamp", "meter_id", "energy_consumption"]].copy()
    out["anomaly_flag"] = (labels == -1).astype(int)
    out["anomaly_score"] = np.round(-scores * 10, 4)
    out["anomaly_type"] = np.where(out["anomaly_flag"] == 1, "abnormal_meter_behaviour", "normal")
    out["detection_method"] = "isolation_forest"
    return out


def detect(df: pd.DataFrame | None = None) -> pd.DataFrame:
    config = load_config()
    frame = df if df is not None else load_ml_features()

    zscores = zscore_anomalies(frame, config["anomaly"]["zscore_threshold"])
    forest = isolation_forest_anomalies(
        frame, config["anomaly"]["contamination"], config["ml"]["random_state"]
    )
    combined = pd.concat([zscores, forest], ignore_index=True)
    combined["anomaly_severity"] = combined["anomaly_score"].map(_severity)
    combined.loc[combined["anomaly_flag"] == 0, "anomaly_severity"] = "none"
    combined = combined.sort_values(["timestamp", "meter_id", "detection_method"]).reset_index(drop=True)
    logger.info(
        "Detected %d anomalies out of %d scored rows",
        int(combined["anomaly_flag"].sum()),
        len(combined),
    )
    return combined


def store_anomalies(frame: pd.DataFrame) -> int:
    payload = frame.rename(columns={"timestamp": "reading_ts"})[
        [
            "reading_ts", "meter_id", "energy_consumption", "anomaly_flag",
            "anomaly_type", "anomaly_score", "anomaly_severity", "detection_method",
        ]
    ]
    # Only persist actual anomalies to keep the fact table analytical.
    payload = payload[payload["anomaly_flag"] == 1]
    with get_connection() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {schema()}.fact_anomalies")
    payload.to_sql(
        "fact_anomalies", get_engine(), schema=schema(), if_exists="append", index=False, chunksize=5000
    )
    logger.info("Stored %d anomalies in PostgreSQL", len(payload))
    return len(payload)


def run() -> dict:
    config = load_config()
    frame = detect()
    anomalies = frame[frame["anomaly_flag"] == 1].reset_index(drop=True)
    paths = write_gold(anomalies, PROJECT_ROOT / config["paths"]["gold"], "anomalies")
    stored = store_anomalies(frame)
    summary = {
        "scored_rows": int(len(frame)),
        "anomalies": int(len(anomalies)),
        "stored_in_postgres": stored,
        "by_type": anomalies["anomaly_type"].value_counts().to_dict(),
        "by_severity": anomalies["anomaly_severity"].value_counts().to_dict(),
        "gold_files": paths,
    }
    logger.info("Anomaly stage complete: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run anomaly detection")
    parser.parse_args()
    print(json.dumps(run(), indent=2, default=str))


if __name__ == "__main__":
    main()
