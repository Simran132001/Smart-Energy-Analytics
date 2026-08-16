#!/usr/bin/env bash
# Execute the Hive DDL scripts in order (requires a reachable HiveServer2 / hive CLI).
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v hive >/dev/null 2>&1 && ! command -v beeline >/dev/null 2>&1; then
  echo "Neither 'hive' nor 'beeline' found. Run these scripts on your Hadoop/Databricks cluster:"
  ls -1 "${PROJECT_ROOT}"/sql/hive/*.hql
  exit 0
fi

for script in "${PROJECT_ROOT}"/sql/hive/*.hql; do
  echo "Applying ${script}"
  if command -v beeline >/dev/null 2>&1; then
    beeline -u "${HIVE_JDBC_URL:-jdbc:hive2://localhost:10000}" -f "${script}"
  else
    hive -f "${script}"
  fi
done
