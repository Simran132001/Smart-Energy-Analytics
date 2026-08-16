"""Final Power BI consolidation step.

Builds the flat fact table Power BI binds to (consumption + prediction +
anomaly + weather in one grain) and refreshes the star-schema exports.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import write_gold
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_powerbi_fact(gold_dir: Path) -> pd.DataFrame:
    hourly = pd.read_parquet(gold_dir / "hourly_consumption.parquet")
    features = pd.read_parquet(gold_dir / "ml_features.parquet")[
        [
            "timestamp", "meter_id", "temperature", "humidity", "weather_condition",
            "temperature_band", "season", "weekend_flag", "day_of_week",
        ]
    ]
    features["date"] = pd.to_datetime(features["timestamp"]).dt.date
    features["hour"] = pd.to_datetime(features["timestamp"]).dt.hour

    fact = hourly.merge(
        features.drop(columns=["timestamp"]), on=["date", "hour", "meter_id"], how="left"
    )

    predictions_path = gold_dir / "predictions.parquet"
    if predictions_path.exists():
        predictions = pd.read_parquet(predictions_path)
        predictions["date"] = pd.to_datetime(predictions["timestamp"]).dt.date
        predictions["hour"] = pd.to_datetime(predictions["timestamp"]).dt.hour
        fact = fact.merge(
            predictions[
                ["date", "hour", "meter_id", "predicted_consumption", "prediction_error",
                 "abs_percentage_error", "model_name"]
            ],
            on=["date", "hour", "meter_id"],
            how="left",
        )

    anomalies_path = gold_dir / "anomalies.parquet"
    if anomalies_path.exists():
        anomalies = pd.read_parquet(anomalies_path)
        anomalies["date"] = pd.to_datetime(anomalies["timestamp"]).dt.date
        anomalies["hour"] = pd.to_datetime(anomalies["timestamp"]).dt.hour
        aggregated = (
            anomalies.sort_values("anomaly_score", key=lambda s: s.abs(), ascending=False)
            .groupby(["date", "hour", "meter_id"], as_index=False)
            .agg(
                anomaly_flag=("anomaly_flag", "max"),
                anomaly_type=("anomaly_type", "first"),
                anomaly_score=("anomaly_score", "first"),
                anomaly_severity=("anomaly_severity", "first"),
            )
        )
        fact = fact.merge(aggregated, on=["date", "hour", "meter_id"], how="left")

    fact["anomaly_flag"] = fact.get("anomaly_flag", 0)
    fact["anomaly_flag"] = fact["anomaly_flag"].fillna(0).astype(int)
    fact["anomaly_type"] = fact.get("anomaly_type", "normal")
    fact["anomaly_type"] = fact["anomaly_type"].fillna("normal")
    fact["anomaly_severity"] = fact.get("anomaly_severity", "none")
    fact["anomaly_severity"] = fact["anomaly_severity"].fillna("none")
    fact["date"] = pd.to_datetime(fact["date"])
    fact = fact.drop_duplicates(subset=["date", "hour", "meter_id"]).reset_index(drop=True)
    return fact


def run(gold_dir: str | Path | None = None) -> dict:
    config = load_config()
    directory = Path(gold_dir) if gold_dir else PROJECT_ROOT / config["paths"]["gold"]

    fact = build_powerbi_fact(directory)
    paths = write_gold(fact, directory, "powerbi_fact_consumption")

    summary = {
        "rows": int(len(fact)),
        "columns": list(fact.columns),
        "anomaly_rows": int(fact["anomaly_flag"].sum()),
        "predicted_rows": int(fact["predicted_consumption"].notna().sum())
        if "predicted_consumption" in fact
        else 0,
        "files": paths,
    }
    logger.info("Power BI fact table built: %d rows", len(fact))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the flat Power BI fact table")
    parser.add_argument("--gold-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.gold_dir), indent=2))


if __name__ == "__main__":
    main()
