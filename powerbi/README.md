# Power BI layer

Everything in this folder is prepared so the only remaining manual work is:
**open Power BI Desktop → Get Data → import the Gold files (or connect to PostgreSQL) →
drop the pre-specified visuals onto the four pages.**

No cleaning, ETL, SQL transformation, ML or backend work is required.

## 1. Data to import

| Source | Purpose |
| --- | --- |
| `data/gold/powerbi_fact_consumption.parquet` | Flat hourly fact (consumption + weather + prediction + anomaly) — the fastest single-table start |
| `data/gold/dim_date.parquet` | Date dimension |
| `data/gold/dim_meter.parquet` | Meter dimension |
| `data/gold/daily_consumption.parquet` | Daily trend fact |
| `data/gold/monthly_consumption.parquet` | Monthly trend fact |
| `data/gold/meter_consumption.parquet` | Meter ranking |
| `data/gold/peak_offpeak_consumption.parquet` | Peak vs off-peak |
| `data/gold/weather_energy.parquet` | Weather/energy analysis |
| `data/gold/predictions.parquet` | Actual vs predicted |
| `data/gold/anomalies.parquet` | Anomaly detail |
| `data/gold/energy_summary.parquet` | Single-row KPI summary |

CSV twins of every file are in the same folder for environments where Parquet is not enabled.

Alternatively use **DirectQuery/Import against PostgreSQL** — the views in
`sql/postgres/02_analytics_views.sql` (`vw_*`) match these datasets one-to-one, and
`powerbi/sql_views.sql` lists the exact statements Power BI should bind to.

## 2. Files here

| File | Contents |
| --- | --- |
| `relationships.json` | Table relationships + cardinality to create in the Model view |
| `dax_measures.dax` | All measures, ready to paste |
| `calculated_columns.dax` | Calculated columns |
| `field_mappings.json` | Which field feeds which visual on which page |
| `dashboard_layout.json` | Page-by-page visual specification (type, fields, position) |
| `sql_views.sql` | PostgreSQL views to bind to when using a live connection |
| `import_gold_data.pq` | Power Query M script that loads every Gold file in one step |
| `generate_powerbi_assets.py` | Regenerates this folder's data-dependent artefacts |

## 3. Automation status

Power BI Desktop `.pbix` files cannot be generated from Linux/CI — the format requires the
Windows Power BI Desktop client or the Fabric/Power BI REST API with a workspace. This project
therefore automates everything up to that boundary: cleaned Gold data, SQL views, the complete
Power Query import script, all DAX, relationships and a machine-readable visual layout.

To finish in Power BI Desktop:
1. *Home → Transform data → Advanced Editor* → paste `import_gold_data.pq` (adjust `GoldFolder`).
2. *Model view* → create the relationships listed in `relationships.json`.
3. *Modeling → New measure* → paste each measure from `dax_measures.dax`.
4. Build the four pages using `dashboard_layout.json`.
