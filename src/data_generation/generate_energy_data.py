"""Synthetic smart-meter dataset generator.

Produces realistic hourly readings with daily/seasonal patterns, weather
influence, peak-hour behaviour, per-meter differences and injected anomalies.
"""
from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.io_utils import ensure_dir
from src.utils.logger import get_logger

logger = get_logger(__name__)

METER_TYPES = ["residential", "commercial", "industrial"]
WEATHER_CONDITIONS = ["Clear", "Cloudy", "Rain", "Storm", "Fog", "Snow"]
PEAK_HOURS = set(range(7, 11)) | set(range(17, 22))


def _season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"


def _meter_catalog(n_meters: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(n_meters):
        meter_type = METER_TYPES[i % len(METER_TYPES)]
        base = {"residential": 1.4, "commercial": 3.6, "industrial": 6.8}[meter_type]
        rows.append(
            {
                "meter_id": f"MTR-{i + 1:03d}",
                "meter_type": meter_type,
                "region": ["North", "South", "East", "West"][i % 4],
                "installation_date": (
                    pd.Timestamp("2018-01-01") + pd.Timedelta(days=int(rng.integers(0, 1500)))
                ).date(),
                "rated_voltage": 230.0,
                "base_load_kwh": round(base * float(rng.uniform(0.85, 1.15)), 3),
            }
        )
    return pd.DataFrame(rows)


def _weather_frame(index: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    day_of_year = index.dayofyear.to_numpy()
    hour = index.hour.to_numpy()
    seasonal = 12.0 * np.sin(2 * math.pi * (day_of_year - 100) / 365.0)
    daily = 5.0 * np.sin(2 * math.pi * (hour - 9) / 24.0)
    temperature = 17.0 + seasonal + daily + rng.normal(0, 1.6, len(index))
    humidity = np.clip(72.0 - 0.8 * (temperature - 17.0) + rng.normal(0, 6.0, len(index)), 15, 100)

    conditions = np.empty(len(index), dtype=object)
    for i, temp in enumerate(temperature):
        if temp < 2:
            choices, weights = ["Snow", "Cloudy", "Fog"], [0.5, 0.3, 0.2]
        elif temp > 28:
            choices, weights = ["Clear", "Cloudy", "Storm"], [0.7, 0.2, 0.1]
        else:
            choices, weights = WEATHER_CONDITIONS, [0.34, 0.26, 0.2, 0.07, 0.11, 0.02]
        conditions[i] = rng.choice(choices, p=weights)

    return pd.DataFrame(
        {
            "timestamp": index,
            "temperature": np.round(temperature, 2),
            "humidity": np.round(humidity, 2),
            "weather_condition": conditions,
        }
    )


def generate(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    gen_cfg = config["data_generation"]
    rng = np.random.default_rng(gen_cfg["seed"])

    index = pd.date_range(
        start=gen_cfg["start_date"],
        end=gen_cfg["end_date"],
        freq=f"{gen_cfg['freq_minutes']}min",
        inclusive="left",
    )
    meters = _meter_catalog(gen_cfg["n_meters"], rng)
    weather = _weather_frame(index, rng)

    hour = index.hour.to_numpy()
    dow = index.dayofweek.to_numpy()
    is_weekend = dow >= 5
    is_peak = np.isin(hour, list(PEAK_HOURS))

    frames = []
    for _, meter in meters.iterrows():
        base = meter["base_load_kwh"]
        daily_shape = 1.0 + 0.45 * np.sin(2 * math.pi * (hour - 8) / 24.0) + 0.25 * np.sin(
            4 * math.pi * (hour - 3) / 24.0
        )
        peak_boost = np.where(is_peak, 1.28, 1.0)
        weekend_factor = np.where(
            is_weekend, 1.08 if meter["meter_type"] == "residential" else 0.72, 1.0
        )
        temp = weather["temperature"].to_numpy()
        # Heating below 15C and cooling above 22C both raise consumption.
        weather_factor = 1.0 + 0.022 * np.clip(15.0 - temp, 0, None) + 0.030 * np.clip(
            temp - 22.0, 0, None
        )
        noise = rng.normal(1.0, 0.07, len(index))

        consumption = base * daily_shape * peak_boost * weekend_factor * weather_factor * noise
        consumption = np.clip(consumption, 0.05, None)

        voltage = 230.0 + rng.normal(0, 3.2, len(index)) - 0.7 * (consumption / max(base, 0.1))
        power_factor = np.clip(rng.normal(0.94, 0.03, len(index)), 0.6, 1.0)
        current = (consumption * 1000.0) / (voltage * power_factor)

        anomaly_flag = np.zeros(len(index), dtype=int)
        anomaly_type = np.array(["none"] * len(index), dtype=object)
        n_anomalies = int(len(index) * gen_cfg["anomaly_rate"])
        positions = rng.choice(len(index), size=n_anomalies, replace=False)
        for pos in positions:
            kind = rng.choice(["spike", "drop", "voltage_sag"], p=[0.5, 0.35, 0.15])
            if kind == "spike":
                consumption[pos] *= float(rng.uniform(2.6, 4.5))
            elif kind == "drop":
                consumption[pos] *= float(rng.uniform(0.05, 0.25))
            else:
                voltage[pos] *= float(rng.uniform(0.80, 0.88))
            anomaly_flag[pos] = 1
            anomaly_type[pos] = kind

        hvac = consumption * rng.uniform(0.28, 0.42, len(index))
        lighting = consumption * rng.uniform(0.08, 0.16, len(index))
        appliances = np.clip(consumption - hvac - lighting, 0.0, None)

        frames.append(
            pd.DataFrame(
                {
                    "timestamp": index,
                    "meter_id": meter["meter_id"],
                    "meter_type": meter["meter_type"],
                    "region": meter["region"],
                    "energy_consumption": np.round(consumption, 4),
                    "voltage": np.round(voltage, 2),
                    "current": np.round(current, 3),
                    "power_factor": np.round(power_factor, 3),
                    "temperature": weather["temperature"].to_numpy(),
                    "humidity": weather["humidity"].to_numpy(),
                    "weather_condition": weather["weather_condition"].to_numpy(),
                    "is_peak_hour": is_peak.astype(int),
                    "tariff_period": np.where(is_peak, "peak", "off_peak"),
                    "hvac_kwh": np.round(hvac, 4),
                    "lighting_kwh": np.round(lighting, 4),
                    "appliance_kwh": np.round(appliances, 4),
                    "injected_anomaly": anomaly_flag,
                    "injected_anomaly_type": anomaly_type,
                }
            )
        )

    readings = pd.concat(frames, ignore_index=True)
    readings["season"] = readings["timestamp"].dt.month.map(_season)
    readings = readings.sort_values(["timestamp", "meter_id"]).reset_index(drop=True)
    return readings, meters, weather


def _inject_quality_issues(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Add a small number of dirty records so quality checks are meaningful."""
    dirty = df.copy()
    n = len(dirty)
    null_idx = rng.choice(n, size=max(int(n * 0.002), 5), replace=False)
    dirty.loc[null_idx, "energy_consumption"] = np.nan
    volt_idx = rng.choice(n, size=max(int(n * 0.001), 3), replace=False)
    dirty.loc[volt_idx, "voltage"] = -1.0
    duplicates = dirty.sample(n=max(int(n * 0.001), 5), random_state=7)
    return pd.concat([dirty, duplicates], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic smart-meter data")
    parser.add_argument("--clean", action="store_true", help="Skip dirty-record injection")
    args = parser.parse_args()

    config = load_config()
    readings, meters, weather = generate(config)
    if not args.clean:
        readings = _inject_quality_issues(readings, np.random.default_rng(11))

    raw_dir = ensure_dir(PROJECT_ROOT / config["paths"]["raw"])
    readings.to_csv(raw_dir / "energy_readings.csv", index=False)
    meters.to_csv(raw_dir / "meter_info.csv", index=False)
    weather.to_csv(raw_dir / "weather.csv", index=False)

    logger.info(
        "Generated %d readings, %d meters, %d weather rows into %s",
        len(readings),
        len(meters),
        len(weather),
        raw_dir,
    )
    print(f"raw rows={len(readings)} meters={len(meters)} generated_at={datetime.utcnow().isoformat()}")


if __name__ == "__main__":
    main()
