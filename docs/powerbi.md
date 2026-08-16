# Power BI

## What is automated

`powerbi/` contains everything that can be produced without the Power BI Desktop binary format:

| File | Contents |
| --- | --- |
| `dataset_manifest.json` | The 13 Gold datasets, their paths, row/column counts |
| `import_gold_data.pq` | Power Query M script importing every Gold Parquet file |
| `sql_views.sql` | Equivalent PostgreSQL views for a live/DirectQuery connection |
| `relationships.json` | Table relationships, keys, cardinality and filter direction |
| `dax_measures.dax` | KPI, trend, prediction-accuracy and anomaly measures |
| `calculated_columns.dax` | Calculated columns for the fact and dimension tables |
| `field_mappings.json` | Visual-by-visual field assignments per page |
| `dashboard_layout.json` | Page, visual, slicer and drill-down specification |

`.pbix` is a proprietary binary that Power BI Desktop alone can write, and Desktop is Windows-only
— it is not generated here, and nothing pretends otherwise.

## Model

`powerbi_fact_consumption` (104,832 rows × 26 columns) is the single fact, related many-to-one to
`dim_meter` (`meter_id`) and `dim_date` (`date`), with single-direction filtering. Aggregate Gold
tables (`daily_consumption`, `monthly_consumption`, `meter_consumption`,
`peak_offpeak_consumption`, `weather_energy`, `predictions`, `anomalies`) are available for
page-specific visuals.

## Pages

1. **Executive Overview** — KPI cards (total/average/peak consumption, meters, anomalies, model
   R²), daily trend line, monthly bar, region donut, date and region slicers.
2. **Consumption Analysis** — hourly load profile, weekday vs weekend, seasonal breakdown,
   peak vs off-peak, temperature-band matrix, drill-down month → day → hour.
3. **Meter Analysis** — meter ranking bar, top-10 table, meter type/region comparison,
   per-meter trend with a meter slicer.
4. **Prediction & Anomaly Analysis** — actual vs predicted line, error distribution, accuracy
   cards (MAE/RMSE/R²), anomaly timeline, severity breakdown, anomaly detail table.

## Setup (the only manual work left)

1. Power BI Desktop → **Get Data → Blank Query → Advanced Editor** → paste
   `powerbi/import_gold_data.pq`, adjust the folder path, load.
   *(Live alternative: **Get Data → PostgreSQL**, then select the `vw_*` views.)*
2. **Model view** → create the relationships listed in `relationships.json`.
3. Paste the measures from `dax_measures.dax` and the columns from `calculated_columns.dax`.
4. Build the four pages per `dashboard_layout.json` / `field_mappings.json`, then confirm the
   visual arrangement.
