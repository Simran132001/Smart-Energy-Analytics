"""Explicit Spark schemas for the raw smart-energy feeds."""
from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

RAW_READINGS_SCHEMA = StructType(
    [
        StructField("timestamp", StringType(), True),
        StructField("meter_id", StringType(), True),
        StructField("meter_type", StringType(), True),
        StructField("region", StringType(), True),
        StructField("energy_consumption", DoubleType(), True),
        StructField("voltage", DoubleType(), True),
        StructField("current", DoubleType(), True),
        StructField("power_factor", DoubleType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("weather_condition", StringType(), True),
        StructField("is_peak_hour", IntegerType(), True),
        StructField("tariff_period", StringType(), True),
        StructField("hvac_kwh", DoubleType(), True),
        StructField("lighting_kwh", DoubleType(), True),
        StructField("appliance_kwh", DoubleType(), True),
        StructField("injected_anomaly", IntegerType(), True),
        StructField("injected_anomaly_type", StringType(), True),
        StructField("season", StringType(), True),
    ]
)

METER_SCHEMA = StructType(
    [
        StructField("meter_id", StringType(), True),
        StructField("meter_type", StringType(), True),
        StructField("region", StringType(), True),
        StructField("installation_date", StringType(), True),
        StructField("rated_voltage", DoubleType(), True),
        StructField("base_load_kwh", DoubleType(), True),
    ]
)

WEATHER_SCHEMA = StructType(
    [
        StructField("timestamp", StringType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("weather_condition", StringType(), True),
    ]
)

TIMESTAMP_FORMAT = "yyyy-MM-dd HH:mm:ss"
