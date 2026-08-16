"""Spark session factory that also works on Databricks."""
from __future__ import annotations

from pyspark.sql import SparkSession

from src.utils.config import PROJECT_ROOT, load_config


def get_spark(app_name: str | None = None, enable_hive: bool = False) -> SparkSession:
    """Return an active SparkSession.

    On Databricks an active session already exists and is reused untouched.
    """
    active = SparkSession.getActiveSession()
    if active is not None:
        return active

    config = load_config()["spark"]
    builder = (
        SparkSession.builder.appName(app_name or config["app_name"])
        .master(config["master"])
        .config("spark.sql.shuffle.partitions", config["shuffle_partitions"])
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.warehouse.dir", str(PROJECT_ROOT / "spark-warehouse"))
        .config("spark.driver.memory", "2g")
    )
    if enable_hive:
        builder = builder.enableHiveSupport()
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
