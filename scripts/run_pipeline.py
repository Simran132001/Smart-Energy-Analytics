"""End-to-end orchestration: generate -> bronze -> silver -> gold -> postgres -> ml -> predictions -> anomalies."""
from __future__ import annotations

import argparse
import json
import time

from src.utils.logger import get_logger

logger = get_logger(__name__)


def run(skip_generate: bool = False, skip_train: bool = False, load_db: bool = True) -> dict:
    summary: dict[str, object] = {}
    started = time.time()

    if not skip_generate:
        from src.data_generation import generate_energy_data

        generate_energy_data.main()
        summary["generate"] = "ok"

    from src.ingestion import raw_to_bronze

    summary["bronze"] = raw_to_bronze.run()

    from src.etl import bronze_to_silver, silver_to_gold

    summary["silver"] = bronze_to_silver.run()
    summary["gold"] = silver_to_gold.run()

    if load_db:
        from src.db import load_to_postgres

        summary["postgres"] = load_to_postgres.run()

    if not skip_train:
        from src.ml import train

        summary["training"] = train.run()

    from src.ml import anomaly_detection, predict

    summary["predictions"] = predict.run()
    summary["anomalies"] = anomaly_detection.run()

    from src.etl import gold_powerbi

    summary["powerbi"] = gold_powerbi.run()

    summary["duration_seconds"] = round(time.time() - started, 1)
    logger.info("Pipeline finished in %ss", summary["duration_seconds"])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Smart Energy pipeline")
    parser.add_argument("--skip-generate", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--no-db", action="store_true", help="Skip PostgreSQL loading")
    args = parser.parse_args()
    print(json.dumps(run(args.skip_generate, args.skip_train, not args.no_db), indent=2, default=str))


if __name__ == "__main__":
    main()
