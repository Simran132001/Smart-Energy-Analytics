"""Data-quality check tests."""
from __future__ import annotations

import datetime as dt

import pytest

pytest.importorskip("pyspark")

from src.quality.data_quality import run_quality_checks  # noqa: E402


def _frame(spark, rows):
    columns = [
        "meter_id", "timestamp", "energy_consumption", "voltage", "current", "power_factor",
    ]
    return spark.createDataFrame(rows, columns)


def test_clean_frame_passes(spark):
    rows = [
        ("MTR-001", dt.datetime(2023, 1, 1, 0), 2.0, 230.0, 9.0, 0.95),
        ("MTR-001", dt.datetime(2023, 1, 1, 1), 2.4, 231.0, 9.4, 0.94),
    ]
    report = run_quality_checks(_frame(spark, rows), layer="test")
    assert report.passed
    assert report.total_rows == 2


def test_nulls_and_duplicates_are_reported(spark):
    rows = [
        ("MTR-001", dt.datetime(2023, 1, 1, 0), None, 230.0, 9.0, 0.95),
        ("MTR-001", dt.datetime(2023, 1, 1, 0), 2.0, 230.0, 9.0, 0.95),
        ("BAD", dt.datetime(2023, 1, 1, 2), 2.0, 999.0, 9.0, 0.95),
    ]
    report = run_quality_checks(_frame(spark, rows), layer="test")
    assert not report.passed
    assert report.checks["null_energy_consumption"] == 1
    assert report.checks["duplicate_rows"] == 1
    assert report.checks["invalid_meter_id"] == 1
    assert report.checks["invalid_voltage"] == 1


def test_strict_mode_raises(spark):
    rows = [("MTR-001", dt.datetime(2023, 1, 1, 0), None, 230.0, 9.0, 0.95)]
    with pytest.raises(ValueError):
        run_quality_checks(_frame(spark, rows), layer="test", strict=True)
