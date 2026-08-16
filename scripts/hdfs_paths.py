"""Resolve medallion-layer paths for HDFS, Databricks (DBFS) or the local disk."""
from __future__ import annotations

import argparse
import os

from src.utils.config import PROJECT_ROOT, load_config

LAYERS = ("raw", "bronze", "silver", "gold")


def layer_path(layer: str, backend: str | None = None) -> str:
    if layer not in LAYERS:
        raise ValueError(f"Unknown layer '{layer}', expected one of {LAYERS}")
    config = load_config()
    backend = backend or os.getenv("STORAGE_BACKEND", "local")
    if backend == "hdfs":
        return f"hdfs://{config['hdfs'][layer]}"
    if backend == "dbfs":
        return f"dbfs:{config['hdfs'][layer]}"
    return str(PROJECT_ROOT / config["paths"][layer])


def main() -> None:
    parser = argparse.ArgumentParser(description="Print medallion layer paths")
    parser.add_argument("--backend", default=None, choices=["local", "hdfs", "dbfs"])
    args = parser.parse_args()
    for layer in LAYERS:
        print(f"{layer}\t{layer_path(layer, args.backend)}")


if __name__ == "__main__":
    main()
