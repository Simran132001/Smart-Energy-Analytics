# CDAC Interview Explanation

## 30-second pitch

"I built an end-to-end smart-energy analytics platform. Synthetic smart-meter data is ingested
with PySpark into a Bronze/Silver/Gold medallion architecture on HDFS with Hive tables, the Gold
layer is loaded into a PostgreSQL star schema with analytics views, a scikit-learn model forecasts
hourly consumption and two detectors flag anomalies, a Flask REST API serves it all, and Power BI
consumes the modelled Gold datasets. The whole stack runs under Docker and is covered by pytest."

## Why each technology

* **PySpark** — distributed, schema-enforced processing of meter readings; the same code runs
  locally, on a cluster and on Databricks.
* **HDFS + Hive** — medallion storage with a SQL metastore over it, the classic big-data layout.
* **PostgreSQL** — fast, indexed serving layer for the API and BI; a star schema keeps queries and
  the Power BI model simple.
* **scikit-learn** — the problem is tabular regression; simple, explainable models beat deep
  learning here (Linear Regression won at R² 0.876).
* **Flask** — lightweight REST layer over the warehouse and the model.
* **Power BI** — the business-facing consumption layer.
* **Docker** — reproducible deployment of the API and warehouse together.

## Likely questions

**Why a medallion architecture?** Raw data stays immutable and auditable; each layer has a single
responsibility, so any transformation can be replayed without re-ingesting.

**How do you avoid duplicates on rerun?** Silver deduplicates on `(meter_id, timestamp)` keeping
the latest ingestion, every write overwrites its layer, and PostgreSQL loads truncate then insert
inside a transaction — the pipeline is idempotent.

**How do you handle missing/invalid data?** A quality framework counts nulls, duplicates, invalid
timestamps, meter IDs, energy, voltage and current per layer and can fail the run in strict mode.
Silver imputes missing numerics from the meter's own average and drops records that violate
physical bounds.

**Why not shuffle the train/test split?** It is a time series — shuffling leaks future readings
into training. The last 20% chronologically is held out.

**Which features matter most?** The 1-hour and 24-hour lags and the 24-hour rolling mean, then
hour-of-day and temperature — consumption is strongly autocorrelated and weather-driven.

**Why did Linear Regression beat the ensembles?** With strong lag features the relationship is
close to linear; the ensembles fit noise and generalised slightly worse on the held-out period.

**How does anomaly detection work?** A robust per-meter/per-hour z-score (median/MAD, so outliers
don't inflate the threshold) catches spikes and unusual highs/lows, and an Isolation Forest over
the electrical and weather features catches multivariate abnormal behaviour.

**How would you scale it?** Partition Bronze/Silver by date, run Spark on YARN or Databricks,
partition the PostgreSQL facts by month, and schedule the pipeline; the API scales horizontally
behind Gunicorn since it is stateless.

**What would you improve next?** Streaming ingestion, per-meter models with automatic retraining,
MLflow tracking and alerting on high-severity anomalies.
