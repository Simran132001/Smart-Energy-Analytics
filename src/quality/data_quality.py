"""Reusable Spark data-quality checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityReport:
    layer: str
    total_rows: int
    checks: Dict[str, int] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)

    def add(self, name: str, count: int, fail_on_positive: bool = True) -> None:
        self.checks[name] = count
        if fail_on_positive and count > 0:
            self.failures.append(f"{name}={count}")

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "total_rows": self.total_rows,
            "checks": self.checks,
            "failures": self.failures,
            "passed": self.passed,
        }


def run_quality_checks(df: DataFrame, layer: str, strict: bool = False) -> QualityReport:
    """Profile a readings DataFrame and record violations of the configured bounds."""
    limits = load_config()["quality"]
    report = QualityReport(layer=layer, total_rows=df.count())

    key_columns = ["timestamp", "meter_id", "energy_consumption"]
    for column in key_columns:
        report.add(f"null_{column}", df.filter(F.col(column).isNull()).count())

    report.add(
        "duplicate_rows",
        df.groupBy("timestamp", "meter_id").count().filter(F.col("count") > 1).count(),
    )
    report.add("invalid_timestamp", df.filter(F.col("timestamp").isNull()).count())
    report.add("invalid_meter_id", df.filter(~F.col("meter_id").rlike(r"^MTR-\d{3}$")).count())
    report.add(
        "invalid_energy",
        df.filter(
            (F.col("energy_consumption") < limits["min_energy"])
            | (F.col("energy_consumption") > limits["max_energy"])
        ).count(),
    )
    report.add(
        "invalid_voltage",
        df.filter(
            (F.col("voltage") < limits["min_voltage"]) | (F.col("voltage") > limits["max_voltage"])
        ).count(),
        fail_on_positive=False,
    )
    report.add(
        "invalid_current",
        df.filter(
            (F.col("current") < limits["min_current"]) | (F.col("current") > limits["max_current"])
        ).count(),
        fail_on_positive=False,
    )
    report.add(
        "invalid_power_factor",
        df.filter(
            (F.col("power_factor") < limits["min_power_factor"])
            | (F.col("power_factor") > limits["max_power_factor"])
        ).count(),
        fail_on_positive=False,
    )

    logger.info("Quality report for %s: %s", layer, report.to_dict())
    if strict and not report.passed:
        raise ValueError(f"Data quality failed for layer {layer}: {report.failures}")
    return report
