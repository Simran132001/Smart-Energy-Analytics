"""RAW -> BRONZE ingestion with PySpark.

Reads the generated CSV feeds, applies explicit schemas, parses timestamps,
runs data-quality profiling and writes partitioned Parquet to the Bronze layer.
Works locally and on Databricks (paths can be overridden with --base-path).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.ingestion.schemas import (
    METER_SCHEMA,
    RAW_READINGS_SCHEMA,
    TIMESTAMP_FORMAT,
    WEATHER_SCHEMA,
)
from src.quality.data_quality import run_quality_checks
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark

logger = get_logger(__name__)


def read_raw(spark: SparkSession, raw_dir: str) -> tuple[DataFrame, DataFrame, DataFrame]:
    readings = (
        spark.read.option("header", True)
        .schema(RAW_READINGS_SCHEMA)
        .csv(f"{raw_dir}/energy_readings.csv")
    )
    meters = spark.read.option("header", True).schema(METER_SCHEMA).csv(f"{raw_dir}/meter_info.csv")
    weather = spark.read.option("header", True).schema(WEATHER_SCHEMA).csv(f"{raw_dir}/weather.csv")
    return readings, meters, weather


def to_bronze(readings: DataFrame) -> DataFrame:
    """Type-cast, parse timestamps and stamp ingestion metadata."""
    return (
        readings.withColumn("event_ts", F.to_timestamp("timestamp", TIMESTAMP_FORMAT))
        .withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("source_system", F.lit("smart_meter_csv"))
        .withColumn("event_date", F.to_date("event_ts"))
        .drop("timestamp")
        .withColumnRenamed("event_ts", "timestamp")
    )


def run(base_path: str | None = None, strict: bool = False) -> dict:
    config = load_config()
    root = Path(base_path) if base_path else PROJECT_ROOT
    raw_dir = str(root / config["paths"]["raw"])
    bronze_dir = str(root / config["paths"]["bronze"])

    spark = get_spark("raw_to_bronze")
    readings, meters, weather = read_raw(spark, raw_dir)
    logger.info("Read %d raw reading rows", readings.count())

    bronze = to_bronze(readings)
    report = run_quality_checks(bronze, layer="bronze", strict=strict)

    bronze.write.mode("overwrite").partitionBy("event_date").parquet(f"{bronze_dir}/energy_readings")
    meters.write.mode("overwrite").parquet(f"{bronze_dir}/meter_info")
    weather.withColumn(
        "timestamp", F.to_timestamp("timestamp", TIMESTAMP_FORMAT)
    ).write.mode("overwrite").parquet(f"{bronze_dir}/weather")

    Path(root / "logs").mkdir(parents=True, exist_ok=True)
    with open(root / "logs" / "bronze_quality_report.json", "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)

    logger.info("Bronze layer written to %s", bronze_dir)
    return report.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="RAW -> BRONZE ingestion")
    parser.add_argument("--base-path", default=None, help="Override project root (e.g. /dbfs/...)")
    parser.add_argument("--strict", action="store_true", help="Fail on quality violations")
    args = parser.parse_args()
    print(json.dumps(run(args.base_path, args.strict), indent=2))


if __name__ == "__main__":
    main()
