# Databricks notebook source
# MAGIC %md
# MAGIC # Smart Energy Analytics - Databricks pipeline
# MAGIC Runs the same medallion pipeline used locally. Attach this notebook to a
# MAGIC cluster with the repo synced via Databricks Repos, then run all cells.

# COMMAND ----------

# MAGIC %pip install -r ../requirements.txt

# COMMAND ----------

import os
import sys

# Repos checkout root, e.g. /Workspace/Repos/<user>/Smart-Energy-Analytics
REPO_ROOT = os.path.abspath("..")
sys.path.insert(0, REPO_ROOT)
os.environ["STORAGE_BACKEND"] = "dbfs"

# COMMAND ----------

from src.data_generation import generate_energy_data
from src.ingestion import raw_to_bronze
from src.etl import bronze_to_silver, silver_to_gold

# COMMAND ----------

# MAGIC %md ## 1. Generate raw data (skip if raw already lands on DBFS)

# COMMAND ----------

generate_energy_data.main()

# COMMAND ----------

# MAGIC %md ## 2. RAW -> BRONZE

# COMMAND ----------

raw_to_bronze.run(base_path="/dbfs/smart_energy")

# COMMAND ----------

# MAGIC %md ## 3. BRONZE -> SILVER

# COMMAND ----------

bronze_to_silver.run(base_path="/dbfs/smart_energy")

# COMMAND ----------

# MAGIC %md ## 4. SILVER -> GOLD

# COMMAND ----------

silver_to_gold.run(base_path="/dbfs/smart_energy")

# COMMAND ----------

# MAGIC %md ## 5. Register Hive tables

# COMMAND ----------

for statement in open(f"{REPO_ROOT}/sql/hive/02_create_tables.hql").read().split(";"):
    if statement.strip():
        spark.sql(statement)  # noqa: F821  (spark provided by Databricks)
