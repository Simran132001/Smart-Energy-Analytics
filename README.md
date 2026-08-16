# Smart Energy Analytics & Consumption Prediction Platform

End-to-end big-data + machine-learning platform for smart-meter energy data: synthetic data
generation → PySpark medallion ETL (Bronze/Silver/Gold) on an HDFS/Hive layout → PostgreSQL
analytics warehouse → scikit-learn consumption forecasting and anomaly detection → Flask REST
API → Power BI-ready Gold datasets, DAX and dashboard specification → Docker.

## 1. Project Overview

The platform ingests raw smart-meter readings, cleans and conforms them through a medallion
architecture, publishes analytics-ready Gold datasets, trains and selects a consumption
prediction model, detects abnormal meter behaviour, serves everything over a REST API and hands
Power BI a modelled, typed, duplicate-free star schema.

## 2. Problem Statement

Utilities collect millions of raw meter readings that are noisy, duplicated and unusable for
reporting. Without a governed pipeline there is no reliable view of consumption trends, no
forecast of future load and no automated way to spot meter faults, energy theft or equipment
failure.

## 3. Business Objective

* Track total, average, peak and off-peak consumption across meters, regions and time.
* Forecast hourly consumption per meter to support load planning and tariff decisions.
* Detect consumption anomalies early to reduce losses and maintenance cost.
* Deliver a self-service Power BI dashboard on a trusted, pre-modelled dataset.

## 4. Features

* Realistic synthetic smart-meter generator (daily/seasonal/weather/peak patterns + anomalies).
* PySpark RAW → BRONZE ingestion with explicit schema, typing and error handling.
* Data-quality framework (nulls, duplicates, invalid timestamps/meters/energy/voltage/current).
* BRONZE → SILVER cleaning, deduplication, imputation and calendar/season enrichment.
* SILVER → GOLD aggregations: hourly, daily, weekly, monthly, meter, peak/off-peak, weather.
* HDFS medallion directory layout with a local mirror fallback, plus Hive DDL.
* PostgreSQL warehouse with PKs, FKs, constraints, indexes and 14 analytics views.
* Time-aware ML pipeline comparing Linear Regression, Random Forest and Gradient Boosting.
* Prediction and anomaly results persisted to both Gold files and PostgreSQL.
* Flask REST API with validation, error handling, logging and health checks.
* Power BI assets: fact/dim datasets, relationships, DAX measures, field mappings, layout spec.
* Docker + docker compose for API and warehouse; pytest suite covering every layer.

## 5. Architecture

```text
Synthetic Data  →  RAW (CSV)
                     ↓  PySpark ingestion + quality checks
                   BRONZE (Parquet, HDFS /bronze)
                     ↓  clean · dedupe · impute · enrich
                   SILVER (Parquet, HDFS /silver)
                     ↓  aggregate · dimension · feature build
                   GOLD (CSV + Parquet, HDFS /gold, Hive tables)
                     ↓                       ↓
        PostgreSQL warehouse          scikit-learn ML
        (facts, dims, views)     (train → select → predict → anomalies)
                     ↓                       ↓
                     └────→ Flask REST API ←─┘
                                 ↓
                      Power BI (Gold files or live PostgreSQL views)
```

Details: [docs/architecture.md](docs/architecture.md).

## 6. Technology Stack

Python 3.10 · PySpark 3.5 (Apache Spark) · Hadoop HDFS · Hive · Databricks-compatible notebook ·
PostgreSQL 14+ · SQL · pandas · scikit-learn · joblib · Flask · Gunicorn · Docker &
docker compose · pytest · Power BI (DAX / Power Query M) · Git & GitHub.

## 7. Folder Structure

```text
config/       config.yaml — paths, spark, hive, quality thresholds, ML and anomaly settings
data/         raw/ bronze/ silver/ gold/ + hdfs_mirror/ (local HDFS fallback)
docker/       Docker usage notes
docs/         architecture, database, api, ml, powerbi, deployment, github, cdac guides
logs/         rotating application log output
models/       best_model.joblib + model_metrics.json (artifacts are git-ignored)
notebooks/    databricks_pipeline.py — Databricks-runnable end-to-end pipeline
powerbi/      Gold manifest, relationships, DAX, calculated columns, mappings, layout, M script
scripts/      hdfs_setup.sh, run_hive_ddl.sh, hdfs_paths.py, run_pipeline.py
sql/          hive/ DDL and postgres/ schema + analytics views
src/          api/ data_generation/ db/ etl/ ingestion/ ml/ quality/ utils/
tests/        pytest suite for quality, ETL, warehouse, ML, API and Gold/Power BI readiness
```

## 8. Dataset Description

Hourly readings for 12 meters across a full year (~105k rows after cleaning).

| Column | Description |
| --- | --- |
| `timestamp` | Reading timestamp (hourly) |
| `meter_id` | Meter identifier (`MTR-001` …) |
| `meter_type`, `region` | Residential/commercial/industrial, geographic region |
| `energy_consumption` | kWh consumed in the interval |
| `voltage`, `current`, `power_factor` | Electrical measurements |
| `temperature`, `humidity`, `weather_condition` | Weather context |
| `is_peak_hour`, `tariff_period` | Peak/off-peak information |
| `hvac_kwh`, `lighting_kwh`, `appliance_kwh` | Appliance/sub-meter split |
| `season`, `injected_anomaly` | Season label and ground-truth anomaly marker |

The generator injects controlled spikes, drops, voltage sags, nulls and duplicates so the
quality framework and anomaly detector have something real to catch.

## 9. ETL Workflow

1. **RAW → BRONZE** (`src/ingestion/raw_to_bronze.py`): explicit schema, timestamp parsing, type
   casting, ingestion metadata, quality report.
2. **BRONZE → SILVER** (`src/etl/bronze_to_silver.py`): deduplicate on `(meter_id, timestamp)`
   keeping the latest ingestion, impute missing numerics per meter, normalise categoricals,
   bound-check electrical values, derive `date/year/month/day/hour/minute/day_of_week/
   weekend_flag/peak_hour_flag/season/temperature_band`.
3. **SILVER → GOLD** (`src/etl/silver_to_gold.py`): hourly, daily, weekly, monthly, meter-wise,
   peak/off-peak, weather analytics, `dim_date`, `dim_meter`, `energy_summary`, `ml_features`.
4. **GOLD → Power BI fact** (`src/etl/gold_powerbi.py`): single wide `powerbi_fact_consumption`
   joining hourly consumption, weather, calendar, meter attributes, predictions and anomalies.

Every stage is idempotent — reruns overwrite their layer and reload PostgreSQL by truncation.

## 10. HDFS

`scripts/hdfs_setup.sh` creates `/user/smart_energy/{raw,bronze,silver,gold}` with `hdfs dfs`
when Hadoop is present, and otherwise mirrors the same tree under `data/hdfs_mirror/` so the
pipeline runs unchanged on a single machine. `scripts/hdfs_paths.py` resolves layer paths for
both modes.

## 11. Hive

`sql/hive/` creates the `smart_energy` database, external Bronze/Silver tables over the medallion
directories, dimension tables and Gold aggregation tables (hourly, daily, monthly, meter,
peak/off-peak, weather, predictions, anomalies). Apply with `scripts/run_hive_ddl.sh`.

## 12. PostgreSQL

Star schema with `dim_meter`/`dim_date`, nine fact tables, `energy_summary`, primary and foreign
keys, check constraints and indexes on the join/filter columns, plus 14 analytics views
(`vw_energy_summary`, `vw_daily_trend`, `vw_monthly_trend`, `vw_hourly_pattern`,
`vw_meter_ranking`, `vw_top_meters`, `vw_peak_offpeak`, `vw_weekday_weekend`,
`vw_seasonal_consumption`, `vw_weather_impact`, `vw_anomaly_counts`, `vw_anomaly_by_meter`,
`vw_prediction_accuracy`, `vw_actual_vs_predicted`). Details: [docs/database.md](docs/database.md).

## 13. ML Workflow

Features: electrical readings, weather, calendar, peak/weekend flags, lags (1h, 2h, 3h, 24h),
rolling mean/std (3h, 24h), cyclical hour/month/day encodings and one-hot categoricals — 38
features in total. Chronological 80/20 split (never shuffled). Linear Regression, Random Forest
and Gradient Boosting are trained and compared on MAE/MSE/RMSE/R², and the best model is saved to
`models/best_model.joblib`. Details: [docs/ml.md](docs/ml.md).

## 14. Prediction

`src/ml/predict.py` scores batches or a single payload; for single requests the recent history of
the meter is loaded to populate lag and rolling features. Results land in
`data/gold/predictions.{csv,parquet}` and `fact_predictions`, with actual, predicted, error and
model name per row.

## 15. Anomaly Detection

Two complementary detectors (`src/ml/anomaly_detection.py`): a robust per-meter/per-hour
z-score catching sudden spikes and unusually high/low consumption, and an Isolation Forest over
consumption, voltage, current, power factor, temperature and humidity catching abnormal meter
behaviour. Output is typed (`sudden_spike`, `high_consumption`, `low_consumption`,
`abnormal_behaviour`) and severity-scored, then written to Gold and `fact_anomalies`.

## 16. Flask API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Database + model health |
| GET | `/api/energy/summary` | Headline KPIs |
| GET | `/api/energy/daily` | Daily consumption trend |
| GET | `/api/energy/monthly` | Monthly consumption trend |
| GET | `/api/energy/hourly` | Average hourly load profile |
| GET | `/api/meters` | Meter catalogue with ranking |
| GET | `/api/meters/<meter_id>` | Single meter detail |
| GET | `/api/anomalies` | Anomalies (filter by severity/meter/limit) |
| GET | `/api/predictions` | Predictions + accuracy summary |
| POST | `/api/predict` | Predict consumption for a new input |

Full request/response reference: [docs/api.md](docs/api.md).

## 17. Gold Datasets

`data/gold/` (CSV **and** Parquet): `energy_summary`, `hourly_consumption`, `daily_consumption`,
`weekly_consumption`, `monthly_consumption`, `meter_consumption`, `peak_offpeak_consumption`,
`weather_energy`, `dim_date`, `dim_meter`, `ml_features`, `predictions`, `anomalies`,
`powerbi_fact_consumption`. All are cleaned, typed, deduplicated and directly importable.

## 18. Power BI

`powerbi/` ships the dataset manifest, `relationships.json`, `dax_measures.dax`,
`calculated_columns.dax`, `field_mappings.json`, `dashboard_layout.json` (Executive Overview,
Consumption Analysis, Meter Analysis, Prediction & Anomaly Analysis), `import_gold_data.pq` and
`sql_views.sql` for a live PostgreSQL connection. `.pbix` binaries cannot be generated on Linux,
so the remaining manual work is limited to importing the data and confirming the visual layout —
see [docs/powerbi.md](docs/powerbi.md) and `powerbi/README.md`.

## 19. Docker

`Dockerfile` builds the API image (Gunicorn, bundled model and Gold data, healthcheck);
`docker-compose.yml` runs PostgreSQL 15 with the schema auto-applied plus the API, wired through
environment variables and volume mounts. See `docker/README.md` and
[docs/deployment.md](docs/deployment.md).

## 20. Git / GitHub

Repository: <https://github.com/Simran132001/Smart-Energy-Analytics>. Branching, commit
conventions and the push workflow are documented in [docs/github.md](docs/github.md). Secrets are
never committed — `.env`, model binaries and large generated data are git-ignored.

## 21. Installation

```bash
git clone https://github.com/Simran132001/Smart-Energy-Analytics.git
cd Smart-Energy-Analytics
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit credentials
createdb smart_energy         # or use docker compose (section 19)
psql -d smart_energy -f sql/postgres/01_schema.sql
psql -d smart_energy -f sql/postgres/02_analytics_views.sql
```

Requires Python 3.10+, Java 17 (for Spark) and PostgreSQL 14+.

## 22. Execution

```bash
# Everything, in order
PYTHONPATH=. python scripts/run_pipeline.py

# Or stage by stage
python -m src.data_generation.generate_energy_data   # RAW
python -m src.ingestion.raw_to_bronze                # BRONZE
python -m src.etl.bronze_to_silver                   # SILVER
python -m src.etl.silver_to_gold                     # GOLD
python -m src.ml.train                               # train + select best model
python -m src.ml.predict                             # predictions → Gold + PostgreSQL
python -m src.ml.anomaly_detection                   # anomalies → Gold + PostgreSQL
python -m src.db.load_to_postgres                    # load Gold into the warehouse
python -m src.etl.gold_powerbi                       # Power BI fact table
python powerbi/generate_powerbi_assets.py            # Power BI manifest
python -m src.api.app                                # Flask API on :5000
```

`bash scripts/hdfs_setup.sh` and `bash scripts/run_hive_ddl.sh` prepare the HDFS/Hive layer;
`notebooks/databricks_pipeline.py` runs the same pipeline on Databricks.

## 23. Testing

```bash
PYTHONPATH=. pytest            # full suite
PYTHONPATH=. pytest tests/test_api.py -v
```

Coverage: config and data generation, data-quality checks, PySpark Silver/Gold transformations,
PostgreSQL tables/views/integrity, feature engineering, model loading and prediction, anomaly
detection, Flask endpoints and Gold/Power BI readiness. Tests that need PostgreSQL, the trained
model or built Gold files skip themselves automatically when those are unavailable.

## 24. API Examples

```bash
curl http://localhost:5000/health
curl "http://localhost:5000/api/energy/daily?limit=7"
curl "http://localhost:5000/api/anomalies?severity=high&limit=5"
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2024-01-05 18:00:00","meter_id":"MTR-001","temperature":8.0,"humidity":70.0}'
```

```json
{
  "data": {
    "meter_id": "MTR-001",
    "timestamp": "2024-01-05 18:00:00",
    "predicted_consumption": 3.71,
    "model_name": "LinearRegression"
  },
  "status": "success"
}
```

## 25. ML Metrics

| Model | MAE | MSE | RMSE | R² |
| --- | --- | --- | --- | --- |
| **Linear Regression (selected)** | **0.2460** | **1.4199** | **1.1916** | **0.8758** |
| Random Forest | 0.2609 | 1.5905 | 1.2612 | 0.8609 |
| Gradient Boosting | 0.2701 | 1.5442 | 1.2427 | 0.8649 |

83,635 training rows · 20,909 test rows · 38 features (see `models/model_metrics.json`).

## 26. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `JAVA_HOME is not set` / Spark fails to start | Install JDK 17 and export `JAVA_HOME` |
| `psycopg2.OperationalError` | Check `.env` credentials and that PostgreSQL is running |
| `WARN NativeCodeLoader` / hostname-loopback warnings | Harmless on a single-node local Spark |
| `FileNotFoundError: models/best_model.joblib` | Run `python -m src.ml.train` first |
| Gold/prediction tests skipped | Run `scripts/run_pipeline.py` to build the artifacts |
| `hdfs: command not found` | Expected locally — the script mirrors HDFS under `data/hdfs_mirror/` |
| Power BI shows stale data | Re-run `src.etl.gold_powerbi` and refresh the report |

## 27. Future Enhancements

Streaming ingestion of live meter events, weather-forecast-driven day-ahead prediction,
per-meter model specialisation and automatic retraining, MLflow experiment tracking, row-level
security in Power BI, alerting on high-severity anomalies, and CI/CD with automated Docker image
publishing.
