"""SILVER -> GOLD aggregation.

Produces the Power BI-ready Gold datasets. Every dataset is written to
``data/gold`` as both CSV and Parquet, already cleaned, typed, aggregated and
duplicate free so it can be imported into Power BI without further processing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import ensure_dir
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark

logger = get_logger(__name__)


def _write(df: DataFrame, gold_dir: Path, name: str) -> int:
    """Write a Gold dataset as a single CSV plus Parquet via pandas."""
    pdf = df.toPandas()
    ensure_dir(gold_dir)
    pdf.to_csv(gold_dir / f"{name}.csv", index=False)
    pdf.to_parquet(gold_dir / f"{name}.parquet", index=False)
    logger.info("Gold dataset %s: %d rows", name, len(pdf))
    return len(pdf)


def hourly_consumption(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("date", "hour", "meter_id")
        .agg(
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.round(F.max("energy_consumption"), 4).alias("max_consumption"),
            F.round(F.min("energy_consumption"), 4).alias("min_consumption"),
            F.count("*").alias("reading_count"),
            F.round(F.avg("temperature"), 2).alias("avg_temperature"),
            F.max("peak_hour_flag").alias("peak_hour_flag"),
        )
        .orderBy("date", "hour", "meter_id")
    )


def daily_consumption(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("date", "meter_id")
        .agg(
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.round(F.max("energy_consumption"), 4).alias("max_consumption"),
            F.round(F.min("energy_consumption"), 4).alias("min_consumption"),
            F.count("*").alias("reading_count"),
            F.round(F.avg("temperature"), 2).alias("avg_temperature"),
            F.max("weekend_flag").alias("weekend_flag"),
            F.first("season").alias("season"),
        )
        .orderBy("date", "meter_id")
    )


def weekly_consumption(silver: DataFrame) -> DataFrame:
    return (
        silver.withColumn("year_week", F.weekofyear("timestamp"))
        .groupBy("year", "year_week", "meter_id")
        .agg(
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.count("*").alias("reading_count"),
        )
        .withColumnRenamed("year_week", "week_of_year")
        .orderBy("year", "week_of_year", "meter_id")
    )


def monthly_consumption(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("year", "month", "meter_id")
        .agg(
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.round(F.max("energy_consumption"), 4).alias("max_consumption"),
            F.round(F.min("energy_consumption"), 4).alias("min_consumption"),
            F.count("*").alias("reading_count"),
        )
        .orderBy("year", "month", "meter_id")
    )


def meter_consumption(silver: DataFrame) -> DataFrame:
    aggregated = silver.groupBy("meter_id", "meter_type", "region").agg(
        F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
        F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
        F.round(F.max("energy_consumption"), 4).alias("max_consumption"),
        F.round(F.min("energy_consumption"), 4).alias("min_consumption"),
        F.round(F.stddev("energy_consumption"), 4).alias("stddev_consumption"),
        F.count("*").alias("reading_count"),
    )
    rank_window = Window.orderBy(F.col("total_consumption").desc())
    return aggregated.withColumn("consumption_rank", F.row_number().over(rank_window)).orderBy(
        "consumption_rank"
    )


def peak_offpeak_consumption(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("date", "tariff_period")
        .agg(
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.count("*").alias("reading_count"),
        )
        .orderBy("date", "tariff_period")
    )


def weather_energy(silver: DataFrame) -> DataFrame:
    return (
        silver.groupBy("date", "weather_condition", "temperature_band")
        .agg(
            F.round(F.avg("temperature"), 2).alias("avg_temperature"),
            F.round(F.avg("humidity"), 2).alias("avg_humidity"),
            F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
            F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
            F.count("*").alias("reading_count"),
        )
        .orderBy("date", "weather_condition")
    )


def energy_summary(silver: DataFrame) -> DataFrame:
    return silver.agg(
        F.round(F.sum("energy_consumption"), 3).alias("total_consumption"),
        F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
        F.round(F.max("energy_consumption"), 4).alias("peak_consumption"),
        F.round(F.min("energy_consumption"), 4).alias("min_consumption"),
        F.countDistinct("meter_id").alias("meter_count"),
        F.count("*").alias("reading_count"),
        F.min("timestamp").alias("period_start"),
        F.max("timestamp").alias("period_end"),
    )


def dim_date(silver: DataFrame) -> DataFrame:
    return (
        silver.select(
            "date", "year", "month", "day", "day_of_week", "weekend_flag", "season"
        )
        .dropDuplicates(["date"])
        .withColumn("month_name", F.date_format("date", "MMMM"))
        .withColumn("day_name", F.date_format("date", "EEEE"))
        .withColumn("quarter", F.quarter("date"))
        .orderBy("date")
    )


def dim_meter(silver: DataFrame, meters: DataFrame) -> DataFrame:
    stats = silver.groupBy("meter_id").agg(
        F.round(F.avg("energy_consumption"), 4).alias("avg_consumption"),
        F.round(F.sum("energy_consumption"), 4).alias("total_consumption"),
    )
    return meters.join(stats, on="meter_id", how="left").orderBy("meter_id")


def ml_features(silver: DataFrame) -> DataFrame:
    """Hourly per-meter feature table with lags and rolling means for the ML layer."""
    ordered = Window.partitionBy("meter_id").orderBy("timestamp")
    features = silver.select(
        "timestamp",
        "meter_id",
        "meter_type",
        "region",
        "energy_consumption",
        "voltage",
        "current",
        "power_factor",
        "temperature",
        "humidity",
        "weather_condition",
        "hour",
        "day",
        "month",
        "year",
        "day_of_week",
        "weekend_flag",
        "peak_hour_flag",
        "season",
        "temperature_band",
        "date",
    )
    for lag in (1, 2, 3, 24):
        features = features.withColumn(
            f"lag_{lag}h", F.lag("energy_consumption", lag).over(ordered)
        )
    for window_size in (3, 24):
        rolling = ordered.rowsBetween(-window_size, -1)
        features = features.withColumn(
            f"rolling_mean_{window_size}h", F.avg("energy_consumption").over(rolling)
        ).withColumn(f"rolling_std_{window_size}h", F.stddev("energy_consumption").over(rolling))
    return features.orderBy("timestamp", "meter_id")


def run(base_path: str | None = None) -> dict:
    config = load_config()
    root = Path(base_path) if base_path else PROJECT_ROOT
    silver_dir = str(root / config["paths"]["silver"])
    bronze_dir = str(root / config["paths"]["bronze"])
    gold_dir = ensure_dir(root / config["paths"]["gold"])

    spark = get_spark("silver_to_gold")
    silver = spark.read.parquet(f"{silver_dir}/energy_readings").cache()
    meters = spark.read.parquet(f"{bronze_dir}/meter_info")

    outputs = {
        "energy_summary": energy_summary(silver),
        "hourly_consumption": hourly_consumption(silver),
        "daily_consumption": daily_consumption(silver),
        "weekly_consumption": weekly_consumption(silver),
        "monthly_consumption": monthly_consumption(silver),
        "meter_consumption": meter_consumption(silver),
        "peak_offpeak_consumption": peak_offpeak_consumption(silver),
        "weather_energy": weather_energy(silver),
        "dim_date": dim_date(silver),
        "dim_meter": dim_meter(silver, meters),
        "ml_features": ml_features(silver),
    }

    row_counts = {name: _write(df, gold_dir, name) for name, df in outputs.items()}

    # Persist the partitioned Parquet copies for Hive/HDFS consumers as well.
    for name in ("hourly_consumption", "daily_consumption", "monthly_consumption"):
        outputs[name].write.mode("overwrite").parquet(f"{root / config['paths']['gold']}/hive/{name}")

    with open(root / "logs" / "gold_row_counts.json", "w", encoding="utf-8") as handle:
        json.dump(row_counts, handle, indent=2)
    logger.info("Gold layer complete: %s", row_counts)
    return row_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="SILVER -> GOLD aggregation")
    parser.add_argument("--base-path", default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.base_path), indent=2))


if __name__ == "__main__":
    main()
