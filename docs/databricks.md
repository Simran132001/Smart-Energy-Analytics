# Running on Databricks

1. **Sync the repo** – Databricks → *Repos* → *Add Repo* →
   `https://github.com/Simran132001/Smart-Energy-Analytics`.
2. **Cluster** – DBR 13.3 LTS+ (Spark 3.4/3.5, Python 3.10+). No extra libraries are
   required beyond `requirements.txt`, installed by the first notebook cell.
3. **Storage** – set `STORAGE_BACKEND=dbfs`; medallion paths then resolve to
   `dbfs:/smart_energy/{raw,bronze,silver,gold}` (see `scripts/hdfs_paths.py`).
4. **Run** – open `notebooks/databricks_pipeline.py` and *Run All*. The notebook calls the
   same `src/` modules used locally, so there is no Databricks-specific business logic.
5. **Hive/Unity Catalog** – the last cell registers the tables from `sql/hive/02_create_tables.hql`.
   On Unity Catalog, prefix table names with `<catalog>.<schema>`.
6. **Jobs** – schedule `scripts/run_pipeline.py` as a Databricks Job task
   (`python_file`) for an end-to-end refresh.

The Spark session factory (`src/utils/spark_session.get_spark`) reuses the cluster's
active session, so nothing else needs to change between local and Databricks runs.
