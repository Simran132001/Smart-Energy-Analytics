# Database

PostgreSQL 14+. Schema in `sql/postgres/01_schema.sql`, views in `02_analytics_views.sql`.

## Dimensions

* `dim_meter(meter_id PK, meter_type, region, install_date, ...)`
* `dim_date(date PK, year, month, day, quarter, week, day_of_week, weekend_flag, season)`

## Facts

| Table | Grain |
| --- | --- |
| `fact_hourly_consumption` | date × hour × meter |
| `fact_daily_consumption` | date × meter |
| `fact_monthly_consumption` | year × month × meter |
| `fact_meter_consumption` | meter (lifetime totals + rank) |
| `fact_peak_offpeak` | date × meter × tariff period |
| `fact_weather_energy` | weather condition × temperature band |
| `fact_predictions` | timestamp × meter (actual, predicted, error, model) |
| `fact_anomalies` | timestamp × meter × detection method |
| `energy_summary` | single-row headline KPIs |

Fact tables carry foreign keys to `dim_meter` (and `dim_date` where the grain is daily or finer),
check constraints on non-negative measures and indexes on `meter_id`, `date` and `timestamp`.

## Views

`vw_energy_summary`, `vw_daily_trend`, `vw_monthly_trend`, `vw_hourly_pattern`,
`vw_meter_ranking`, `vw_top_meters`, `vw_peak_offpeak`, `vw_weekday_weekend`,
`vw_seasonal_consumption`, `vw_weather_impact`, `vw_anomaly_counts`, `vw_anomaly_by_meter`,
`vw_prediction_accuracy`, `vw_actual_vs_predicted`.

## Loading

`python -m src.db.load_to_postgres` reads the Gold Parquet files and truncates-then-loads each
table inside a transaction, so reruns never duplicate rows.
