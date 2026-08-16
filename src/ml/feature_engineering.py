"""Feature engineering for consumption forecasting."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

CATEGORICAL_FEATURES = ["meter_type", "season", "weather_condition"]
NUMERIC_FEATURES = [
    "voltage",
    "current",
    "power_factor",
    "temperature",
    "humidity",
    "hour",
    "day",
    "month",
    "day_of_week",
    "weekend_flag",
    "peak_hour_flag",
]
TARGET = "energy_consumption"


def load_ml_features(gold_dir: str | Path | None = None) -> pd.DataFrame:
    config = load_config()
    directory = Path(gold_dir) if gold_dir else PROJECT_ROOT / config["paths"]["gold"]
    df = pd.read_parquet(directory / "ml_features.parquet")
    return df.sort_values(["timestamp", "meter_id"]).reset_index(drop=True)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cyclical encodings so the models see hour/month continuity."""
    out = df.copy()
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    out["dow_sin"] = np.sin(2 * np.pi * out["day_of_week"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["day_of_week"] / 7)
    return out


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute lags/rolling means when they are absent (e.g. API inference)."""
    config = load_config()["ml"]
    out = df.sort_values(["meter_id", "timestamp"]).copy()
    grouped = out.groupby("meter_id")[TARGET]
    for lag in config["lags"]:
        column = f"lag_{lag}h"
        if column not in out.columns:
            out[column] = grouped.shift(lag)
    for window in config["rolling_windows"]:
        mean_col, std_col = f"rolling_mean_{window}h", f"rolling_std_{window}h"
        if mean_col not in out.columns:
            out[mean_col] = grouped.shift(1).rolling(window).mean()
        if std_col not in out.columns:
            out[std_col] = grouped.shift(1).rolling(window).std()
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    lag_cols = [c for c in df.columns if c.startswith(("lag_", "rolling_"))]
    cyclical = [c for c in df.columns if c.endswith(("_sin", "_cos"))]
    return NUMERIC_FEATURES + lag_cols + cyclical


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series | None, pd.DataFrame]:
    """Return (X, y, metadata) ready for scikit-learn."""
    enriched = add_time_features(add_lag_features(df))
    enriched = enriched.dropna(subset=[c for c in enriched.columns if c.startswith(("lag_", "rolling_"))])

    columns = feature_columns(enriched)
    encoded = pd.get_dummies(
        enriched[columns + [c for c in CATEGORICAL_FEATURES if c in enriched.columns]],
        columns=[c for c in CATEGORICAL_FEATURES if c in enriched.columns],
        drop_first=False,
    ).astype(float)

    target = enriched[TARGET] if TARGET in enriched.columns else None
    metadata = enriched[["timestamp", "meter_id"]].reset_index(drop=True)
    logger.info("Built feature matrix: %s", encoded.shape)
    return encoded.reset_index(drop=True), (target.reset_index(drop=True) if target is not None else None), metadata


def time_series_split(
    X: pd.DataFrame, y: pd.Series, metadata: pd.DataFrame, test_size: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
    """Chronological split - never shuffles time-series data."""
    order = metadata["timestamp"].argsort(kind="stable")
    X, y, metadata = X.iloc[order].reset_index(drop=True), y.iloc[order].reset_index(drop=True), metadata.iloc[order].reset_index(drop=True)
    cut = int(len(X) * (1 - test_size))
    return X.iloc[:cut], X.iloc[cut:], y.iloc[:cut], y.iloc[cut:], metadata.iloc[cut:].reset_index(drop=True)
