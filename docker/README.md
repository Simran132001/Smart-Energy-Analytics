# Docker

```bash
# 1. Build and start PostgreSQL + the Flask API
docker compose up --build -d

# 2. Load the Gold data into the containerised warehouse (first run only)
docker compose exec api python -m src.db.load_to_postgres

# 3. Verify
curl http://localhost:5000/health
curl http://localhost:5000/api/energy/summary
```

Notes:
- `sql/postgres/*.sql` is mounted into `/docker-entrypoint-initdb.d`, so the schema and views
  are created automatically the first time the database volume is initialised.
- The API image bundles `models/` and `data/gold/`; both are also bind-mounted so a local
  retrain is picked up without rebuilding.
- Override credentials with a local `.env` (see `.env.example`) — never commit it.
- Stop everything with `docker compose down` (add `-v` to drop the database volume).
