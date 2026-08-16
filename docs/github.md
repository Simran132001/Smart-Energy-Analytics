# Git & GitHub

Repository: <https://github.com/Simran132001/Smart-Energy-Analytics>

## Workflow

```bash
git status && git branch -a          # inspect before changing anything
git checkout -b feature/<topic>      # work on a branch
git add <specific paths>             # never `git add .`
git commit -m "feat: <what and why>"
git push -u origin feature/<topic>   # then open a pull request
```

Existing branches are preserved — nothing is deleted, renamed or force-pushed.

## Commit convention

`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:` — one logical change per commit, message
in the imperative mood.

## What is ignored

`.gitignore` excludes `.env`, `.venv/`, `__pycache__/`, `logs/*.log`, model binaries
(`models/*.joblib`), Spark scratch (`spark-warehouse/`, `metastore_db/`, `derby.log`), the HDFS
mirror, RAW/BRONZE/SILVER data and the oversized `data/gold/ml_features.csv` (its Parquet twin is
tracked). Gold CSV/Parquet files needed by Power BI are committed so the report works on a fresh
clone.

## Secrets

No passwords, API keys or tokens are committed. Credentials come only from `.env`, which is
git-ignored; `.env.example` documents the variable names with placeholder values. Authentication
for pushes uses the local Git credential helper — tokens are never embedded in remote URLs.
