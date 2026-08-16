# Architecture

## Layers

| Layer | Location | Format | Purpose |
| --- | --- | --- | --- |
| RAW | `data/raw/`, HDFS `/raw` | CSV | Untouched generator output, including injected defects |
| BRONZE | `data/bronze/`, HDFS `/bronze` | Parquet | Schema-applied, typed, ingestion-stamped |
| SILVER | `data/silver/`, HDFS `/silver` | Parquet | Deduplicated, imputed, validated, calendar-enriched |
| GOLD | `data/gold/`, HDFS `/gold` | CSV + Parquet | Aggregates, dimensions, ML features, predictions, anomalies |

## Flow

```text
generate_energy_data → raw_to_bronze (+ quality report) → bronze_to_silver (+ quality report)
    → silver_to_gold → { load_to_postgres, ml.train → ml.predict, ml.anomaly_detection }
    → gold_powerbi → generate_powerbi_assets → Flask API / Power BI
```

`scripts/run_pipeline.py` orchestrates the whole chain and logs the row counts of each stage.

## Components

* **Spark session** (`src/utils/spark_session.py`) reuses an active Databricks session when one
  exists and otherwise builds a local session, so the same code runs on a laptop, a cluster or
  Databricks (`notebooks/databricks_pipeline.py`).
* **Configuration** (`config/config.yaml` + `.env`) holds paths, Spark options, Hive names,
  quality thresholds, ML and anomaly parameters. Secrets live only in `.env`.
* **Quality framework** (`src/quality/data_quality.py`) returns a `QualityReport` per layer and
  can fail the run in strict mode.
* **Serving** — PostgreSQL is the analytical serving layer for the API and for live Power BI
  connections; Gold files are the import-mode Power BI source.

## Design decisions

* Medallion architecture keeps raw data immutable and makes every transformation replayable.
* Idempotent stages (overwrite writes, truncate-and-load) mean any stage can be rerun safely.
* Time-series correctness: chronological split, lag/rolling features computed per meter in
  timestamp order, never shuffled.
* Power BI gets one wide fact plus conformed dimensions to keep the report model simple.
