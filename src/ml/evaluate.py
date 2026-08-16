"""Model evaluation helpers and CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.ml.feature_engineering import build_feature_matrix, load_ml_features, time_series_split
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 5),
        "mse": round(mse, 5),
        "rmse": round(float(np.sqrt(mse)), 5),
        "r2": round(float(r2_score(y_true, y_pred)), 5),
    }


def model_path() -> Path:
    config = load_config()
    return PROJECT_ROOT / config["paths"]["models"] / "best_model.joblib"


def evaluate_saved_model() -> dict:
    artifact = joblib.load(model_path())
    X, y, metadata = build_feature_matrix(load_ml_features())
    _, X_test, _, y_test, _ = time_series_split(X, y, metadata, load_config()["ml"]["test_size"])
    X_test = X_test.reindex(columns=artifact["feature_columns"], fill_value=0.0)
    metrics = regression_metrics(y_test.to_numpy(), artifact["model"].predict(X_test))
    logger.info("Evaluation of %s: %s", artifact["model_name"], metrics)
    return {"model_name": artifact["model_name"], "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the saved best model")
    parser.parse_args()
    print(json.dumps(evaluate_saved_model(), indent=2))


if __name__ == "__main__":
    main()
