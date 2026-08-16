# Deployment

## Local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit credentials
PYTHONPATH=. python scripts/run_pipeline.py
PYTHONPATH=. python -m src.api.app
```

## Docker

```bash
docker compose up --build -d              # PostgreSQL 15 + Flask API (Gunicorn)
docker compose exec api python -m src.db.load_to_postgres
curl http://localhost:5000/health
docker compose down                       # add -v to drop the database volume
```

* `sql/postgres/*.sql` is mounted to `/docker-entrypoint-initdb.d`, so schema and views are
  applied on first database initialisation.
* `data/gold`, `models` and `logs` are bind-mounted, so retraining locally is picked up without
  rebuilding the image.
* The image runs a healthcheck against `/health` and serves with two Gunicorn workers.

## Configuration

All runtime settings come from environment variables (see `.env.example`): `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `FLASK_ENV`, `FLASK_PORT`,
`MODEL_PATH`, `LOG_LEVEL`. Never commit `.env`.

## Cluster / Databricks

Run `scripts/hdfs_setup.sh` and `scripts/run_hive_ddl.sh` on the edge node, then submit the ETL
modules with `spark-submit`. On Databricks, import `notebooks/databricks_pipeline.py` — the Spark
helper reuses the existing session and the medallion paths point at DBFS.

## Operations

Logs go to `logs/smart_energy.log` and stdout (`docker compose logs -f api`). Refresh the platform
by rerunning `scripts/run_pipeline.py`; every stage is idempotent.
