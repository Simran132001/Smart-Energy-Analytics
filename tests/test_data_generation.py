"""Tests for the synthetic data generator and configuration."""
from __future__ import annotations

import pandas as pd

from src.data_generation.generate_energy_data import generate
from src.utils.config import load_config


def test_config_has_required_sections():
    config = load_config()
    for section in ("paths", "hdfs", "hive", "spark", "data_generation", "quality", "ml", "anomaly"):
        assert section in config


def test_generate_produces_expected_columns():
    config = load_config()
    config = {**config, "data_generation": {**config["data_generation"], "end_date": "2023-01-05"}}
    readings, meters, weather = generate(config)

    expected = {
        "timestamp", "meter_id", "energy_consumption", "voltage", "current", "power_factor",
        "temperature", "humidity", "weather_condition", "is_peak_hour", "tariff_period",
        "hvac_kwh", "lighting_kwh", "appliance_kwh", "season",
    }
    assert expected.issubset(set(readings.columns))
    assert len(meters) == config["data_generation"]["n_meters"]
    assert not weather.empty


def test_generated_values_are_physically_plausible():
    config = load_config()
    config = {**config, "data_generation": {**config["data_generation"], "end_date": "2023-01-03"}}
    readings, _, _ = generate(config)

    assert (readings["energy_consumption"] > 0).all()
    assert readings["power_factor"].between(0.5, 1.0).all()
    assert readings["humidity"].between(0, 100).all()
    assert pd.api.types.is_datetime64_any_dtype(readings["timestamp"])


def test_anomalies_are_injected():
    config = load_config()
    config = {**config, "data_generation": {**config["data_generation"], "end_date": "2023-03-01"}}
    readings, _, _ = generate(config)
    assert readings["injected_anomaly"].sum() > 0
