"""BRONZE -> SILVER cleansing and enrichment with PySpark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from src.quality.data_quality import run_quality_checks
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark

logger = get_logger(__name__)

PEAK_HOURS = list(range(7, 11)) + list(range(17, 22))


def deduplicate(df: DataFrame) -> DataFrame:
    """Keep the most recently ingested row per (meter_id, timestamp)."""
    window = Window.partitionBy("meter_id", "timestamp").orderBy(F.col("ingestion_ts").desc())
    return df.withColumn("_rn", F.row_number().over(window)).filter(F.col("_rn") == 1).drop("_rn")


def clean(df: DataFrame, limits: dict) -> DataFrame:
    """Drop unusable rows, null-out impossible values and impute gaps per meter."""
    cleaned = df.filter(F.col("timestamp").isNotNull() & F.col("meter_id").rlike(r"^MTR-\d{3}$"))

    cleaned = (
        cleaned.withColumn(
            "voltage",
            F.when(
                (F.col("voltage") >= limits["min_voltage"]) & (F.col("voltage") <= limits["max_voltage"]),
                F.col("voltage"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "current",
            F.when(
                (F.col("current") >= limits["min_current"]) & (F.col("current") <= limits["max_current"]),
                F.col("current"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "power_factor",
            F.when(
                (F.col("power_factor") >= limits["min_power_factor"])
                & (F.col("power_factor") <= limits["max_power_factor"]),
                F.col("power_factor"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "energy_consumption",
            F.when(
                (F.col("energy_consumption") >= limits["min_energy"])
                & (F.col("energy_consumption") <= limits["max_energy"]),
                F.col("energy_consumption"),
            ).otherwise(F.lit(None)),
        )
    )

    meter_window = Window.partitionBy("meter_id")
    for column in ["energy_consumption", "voltage", "current", "power_factor", "temperature", "humidity"]:
        cleaned = cleaned.withColumn(
            column, F.coalesce(F.col(column), F.avg(column).over(meter_window))
        )

    cleaned = cleaned.withColumn(
        "weather_condition",
        F.initcap(F.trim(F.coalesce(F.col("weather_condition"), F.lit("unknown")))),
    ).withColumn("meter_type", F.lower(F.trim(F.col("meter_type"))))

    return cleaned.dropna(subset=["energy_consumption"])


def enrich(df: DataFrame) -> DataFrame:
    """Add the calendar, tariff, season and temperature-band derived columns."""
    enriched = (
        df.withColumn("date", F.to_date("timestamp"))
        .withColumn("year", F.year("timestamp"))
        .withColumn("month", F.month("timestamp"))
        .withColumn("day", F.dayofmonth("timestamp"))
        .withColumn("hour", F.hour("timestamp"))
        .withColumn("minute", F.minute("timestamp"))
        .withColumn("day_of_week", F.dayofweek("timestamp"))
        .withColumn("weekend_flag", F.when(F.dayofweek("timestamp").isin(1, 7), 1).otherwise(0))
        .withColumn("peak_hour_flag", F.when(F.hour("timestamp").isin(PEAK_HOURS), 1).otherwise(0))
    )
    enriched = (
        enriched.withColumn(
            "season",
            F.when(F.col("month").isin(12, 1, 2), "Winter")
            .when(F.col("month").isin(3, 4, 5), "Spring")
            .when(F.col("month").isin(6, 7, 8), "Summer")
            .otherwise("Autumn"),
        )
        .withColumn(
            "temperature_band",
            F.when(F.col("temperature") < 5, "Very Cold")
            .when(F.col("temperature") < 15, "Cold")
            .when(F.col("temperature") < 25, "Mild")
            .when(F.col("temperature") < 32, "Warm")
            .otherwise("Hot"),
        )
        .withColumn(
            "tariff_period", F.when(F.col("peak_hour_flag") == 1, "peak").otherwise("off_peak")
        )
    )
    return enriched


def run(base_path: str | None = None, strict: bool = False) -> dict:
    config = load_config()
    root = Path(base_path) if base_path else PROJECT_ROOT
    bronze_dir = str(root / config["paths"]["bronze"])
    silver_dir = str(root / config["paths"]["silver"])

    spark = get_spark("bronze_to_silver")
    bronze = spark.read.parquet(f"{bronze_dir}/energy_readings")
    logger.info("Bronze rows: %d", bronze.count())

    silver = enrich(clean(deduplicate(bronze), config["quality"]))
    report = run_quality_checks(silver, layer="silver", strict=strict)

    silver.write.mode("overwrite").partitionBy("date").parquet(f"{silver_dir}/energy_readings")
    logger.info("Silver rows written: %d", silver.count())

    with open(root / "logs" / "silver_quality_report.json", "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)
    return report.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="BRONZE -> SILVER processing")
    parser.add_argument("--base-path", default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.base_path, args.strict), indent=2))


if __name__ == "__main__":
    main()
