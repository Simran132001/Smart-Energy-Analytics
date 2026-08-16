#!/usr/bin/env bash
# Create the HDFS medallion directory structure and upload the raw feeds.
# Falls back to a local mirror when the Hadoop client is not installed, so the
# same layout can be exercised in a laptop / CI environment.
set -euo pipefail

BASE="${HDFS_BASE:-/smart_energy}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAYERS=(raw bronze silver gold)

if command -v hdfs >/dev/null 2>&1; then
  echo "Hadoop client found - provisioning HDFS under ${BASE}"
  for layer in "${LAYERS[@]}"; do
    hdfs dfs -mkdir -p "${BASE}/${layer}"
  done
  hdfs dfs -chmod -R 755 "${BASE}"
  hdfs dfs -put -f "${PROJECT_ROOT}/data/raw/"*.csv "${BASE}/raw/"
  hdfs dfs -ls -R "${BASE}"
else
  MIRROR="${PROJECT_ROOT}/data/hdfs_mirror${BASE}"
  echo "Hadoop client not found - creating local mirror at ${MIRROR}"
  for layer in "${LAYERS[@]}"; do
    mkdir -p "${MIRROR}/${layer}"
  done
  cp -f "${PROJECT_ROOT}/data/raw/"*.csv "${MIRROR}/raw/" 2>/dev/null || true
  find "${MIRROR}" -maxdepth 2
fi
