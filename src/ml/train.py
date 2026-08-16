"""Train and compare consumption-prediction models, then persist the best one."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.ml.feature_engineering import build_feature_matrix, load_ml_features, time_series_split
from src.ml.evaluate import regression_metrics
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import ensure_dir
from src.utils.logger import get_logger

logger = get_logger(__name__)
MODEL_VERSION = "1.0.0"


def candidate_models(random_state: int) -> dict[str, Pipeline]:
    return {
        "LinearRegression": Pipeline(
            [("scaler", StandardScaler()), ("model", LinearRegression())]
        ),
        "RandomForest": Pipeline(
            [
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=200,
                        max_depth=18,
                        min_samples_leaf=2,
                        n_jobs=-1,
                        random_state=random_state,
                    ),
                )
            ]
        ),
        "GradientBoosting": Pipeline(
            [
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=250,
                        learning_rate=0.08,
                        max_depth=4,
                        random_state=random_state,
                    ),
                )
            ]
        ),
    }


def run(sample_rows: int | None = None) -> dict:
    config = load_config()
    ml_cfg = config["ml"]

    df = load_ml_features()
    if sample_rows:
        df = df.tail(sample_rows)
    X, y, metadata = build_feature_matrix(df)
    X_train, X_test, y_train, y_test, test_meta = time_series_split(
        X, y, metadata, ml_cfg["test_size"]
    )
    logger.info("Train rows=%d, test rows=%d, features=%d", len(X_train), len(X_test), X.shape[1])

    results = {}
    fitted = {}
    for name, pipeline in candidate_models(ml_cfg["random_state"]).items():
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        results[name] = regression_metrics(y_test.to_numpy(), predictions)
        fitted[name] = pipeline
        logger.info("%s -> %s", name, results[name])

    best_name = min(results, key=lambda name: results[name]["rmse"])
    best_model = fitted[best_name]

    models_dir = ensure_dir(PROJECT_ROOT / config["paths"]["models"])
    artifact = {
        "model": best_model,
        "model_name": best_name,
        "model_version": MODEL_VERSION,
        "feature_columns": list(X.columns),
        "metrics": results[best_name],
        "trained_at": datetime.utcnow().isoformat(),
    }
    joblib.dump(artifact, models_dir / "best_model.joblib")
    for name, pipeline in fitted.items():
        joblib.dump({"model": pipeline, "feature_columns": list(X.columns)}, models_dir / f"{name}.joblib")

    metrics_payload = {
        "best_model": best_name,
        "model_version": MODEL_VERSION,
        "trained_at": artifact["trained_at"],
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_count": int(X.shape[1]),
        "results": results,
    }
    with open(models_dir / "model_metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics_payload, handle, indent=2)

    # Persist the hold-out predictions for the Gold prediction dataset.
    test_predictions = best_model.predict(X_test)
    predictions_frame = test_meta.copy()
    predictions_frame["actual_consumption"] = y_test.to_numpy()
    predictions_frame["predicted_consumption"] = np.round(test_predictions, 4)
    predictions_frame.to_parquet(models_dir / "holdout_predictions.parquet", index=False)

    logger.info("Best model: %s (%s)", best_name, results[best_name])
    return metrics_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Train consumption prediction models")
    parser.add_argument("--sample-rows", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.sample_rows), indent=2))


if __name__ == "__main__":
    main()
