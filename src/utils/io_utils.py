"""Filesystem helpers shared across pipeline stages."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_gold(df: pd.DataFrame, directory: str | Path, name: str) -> dict[str, str]:
    """Persist a Gold dataset as both CSV and Parquet (Power BI friendly)."""
    out_dir = ensure_dir(directory)
    csv_path = out_dir / f"{name}.csv"
    parquet_path = out_dir / f"{name}.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    logger.info("Wrote gold dataset %s (%d rows)", name, len(df))
    return {"csv": str(csv_path), "parquet": str(parquet_path)}
