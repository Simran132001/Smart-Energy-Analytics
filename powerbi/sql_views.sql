-- Views Power BI binds to when using the live PostgreSQL connection.
-- Definitions live in sql/postgres/02_analytics_views.sql and are created by
-- src/db/load_to_postgres.py.
SELECT * FROM energy.vw_energy_summary;
SELECT * FROM energy.vw_daily_trend;
SELECT * FROM energy.vw_monthly_trend;
SELECT * FROM energy.vw_hourly_pattern;
SELECT * FROM energy.vw_meter_ranking;
SELECT * FROM energy.vw_top_meters;
SELECT * FROM energy.vw_peak_offpeak;
SELECT * FROM energy.vw_weekday_weekend;
SELECT * FROM energy.vw_seasonal_consumption;
SELECT * FROM energy.vw_weather_impact;
SELECT * FROM energy.vw_anomaly_counts;
SELECT * FROM energy.vw_anomaly_by_meter;
SELECT * FROM energy.vw_prediction_accuracy;
SELECT * FROM energy.vw_actual_vs_predicted;
