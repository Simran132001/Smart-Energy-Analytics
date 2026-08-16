"""Verify and document the Power BI-ready Gold datasets.

Writes powerbi/dataset_manifest.json describing every Gold file (row counts,
columns, dtypes) so the Power BI model can be validated before import.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_DATASETS = [
    "powerbi_fact_consumption",
    "energy_summary",
    "dim_date",
    "dim_meter",
    "daily_consumption",
    "weekly_consumption",
    "monthly_consumption",
    "hourly_consumption",
    "meter_consumption",
    "peak_offpeak_consumption",
    "weather_energy",
    "predictions",
    "anomalies",
]


def describe(path: Path) -> dict:
    df = pd.read_parquet(path)
    return {
        "rows": int(len(df)),
        "columns": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "null_columns": {c: int(n) for c, n in df.isna().sum().items() if n},
    }


def run(gold_dir: str | Path | None = None) -> dict:
    config = load_config()
    directory = Path(gold_dir) if gold_dir else PROJECT_ROOT / config["paths"]["gold"]

    manifest: dict[str, object] = {"gold_dir": str(directory), "datasets": {}, "missing": []}
    for name in REQUIRED_DATASETS:
        parquet = directory / f"{name}.parquet"
        csv = directory / f"{name}.csv"
        if not parquet.exists():
            manifest["missing"].append(name)
            continue
        entry = describe(parquet)
        entry["parquet"] = str(parquet)
        entry["csv"] = str(csv) if csv.exists() else None
        manifest["datasets"][name] = entry

    output = PROJECT_ROOT / "powerbi" / "dataset_manifest.json"
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    logger.info("Power BI manifest written to %s (missing=%s)", output, manifest["missing"])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Power BI dataset manifest")
    parser.add_argument("--gold-dir", default=None)
    args = parser.parse_args()
    manifest = run(args.gold_dir)
    print(json.dumps({"datasets": list(manifest["datasets"].keys()), "missing": manifest["missing"]}, indent=2))


if __name__ == "__main__":
    main()
