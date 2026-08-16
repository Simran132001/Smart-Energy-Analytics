-- Analytical SQL views consumed by the Flask API and Power BI
SET search_path TO energy, public;

CREATE OR REPLACE VIEW vw_energy_summary AS
SELECT
    SUM(total_consumption)                      AS total_consumption,
    AVG(avg_consumption)                        AS average_consumption,
    MAX(max_consumption)                        AS max_consumption,
    MIN(min_consumption)                        AS min_consumption,
    COUNT(DISTINCT meter_id)                    AS meter_count,
    SUM(reading_count)                          AS reading_count,
    MIN(date_key)                               AS period_start,
    MAX(date_key)                               AS period_end
FROM fact_daily_consumption;

CREATE OR REPLACE VIEW vw_daily_trend AS
SELECT
    date_key,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption,
    MAX(max_consumption)   AS max_consumption,
    MIN(min_consumption)   AS min_consumption,
    AVG(avg_temperature)   AS avg_temperature
FROM fact_daily_consumption
GROUP BY date_key
ORDER BY date_key;

CREATE OR REPLACE VIEW vw_monthly_trend AS
SELECT
    year,
    month,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption
FROM fact_monthly_consumption
GROUP BY year, month
ORDER BY year, month;

CREATE OR REPLACE VIEW vw_hourly_pattern AS
SELECT
    hour,
    AVG(avg_consumption)   AS avg_consumption,
    SUM(total_consumption) AS total_consumption,
    MAX(peak_hour_flag)    AS peak_hour_flag
FROM fact_hourly_consumption
GROUP BY hour
ORDER BY hour;

CREATE OR REPLACE VIEW vw_meter_ranking AS
SELECT
    m.meter_id,
    m.meter_type,
    m.region,
    m.total_consumption,
    m.avg_consumption,
    m.max_consumption,
    m.min_consumption,
    m.consumption_rank,
    RANK() OVER (PARTITION BY m.region ORDER BY m.total_consumption DESC) AS region_rank
FROM fact_meter_consumption m
ORDER BY m.consumption_rank;

CREATE OR REPLACE VIEW vw_top_meters AS
SELECT * FROM vw_meter_ranking WHERE consumption_rank <= 5;

CREATE OR REPLACE VIEW vw_peak_offpeak AS
SELECT
    tariff_period,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption,
    SUM(reading_count)     AS reading_count,
    ROUND(
        100.0 * SUM(total_consumption) / NULLIF(SUM(SUM(total_consumption)) OVER (), 0), 2
    ) AS pct_of_total
FROM fact_peak_offpeak
GROUP BY tariff_period;

CREATE OR REPLACE VIEW vw_weekday_weekend AS
SELECT
    CASE WHEN weekend_flag = 1 THEN 'weekend' ELSE 'weekday' END AS day_group,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption
FROM fact_daily_consumption
GROUP BY weekend_flag;

CREATE OR REPLACE VIEW vw_seasonal_consumption AS
SELECT
    season,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption
FROM fact_daily_consumption
GROUP BY season;

CREATE OR REPLACE VIEW vw_weather_impact AS
SELECT
    weather_condition,
    temperature_band,
    AVG(avg_temperature)   AS avg_temperature,
    AVG(avg_humidity)      AS avg_humidity,
    SUM(total_consumption) AS total_consumption,
    AVG(avg_consumption)   AS avg_consumption
FROM fact_weather_energy
GROUP BY weather_condition, temperature_band
ORDER BY total_consumption DESC;

CREATE OR REPLACE VIEW vw_anomaly_counts AS
SELECT
    DATE(reading_ts)                                            AS date_key,
    COUNT(*) FILTER (WHERE anomaly_flag = 1)                    AS anomaly_count,
    COUNT(*) FILTER (WHERE anomaly_severity = 'high')           AS high_severity_count,
    COUNT(*) FILTER (WHERE anomaly_severity = 'medium')         AS medium_severity_count,
    COUNT(*) FILTER (WHERE anomaly_severity = 'low')            AS low_severity_count
FROM fact_anomalies
GROUP BY DATE(reading_ts)
ORDER BY date_key;

CREATE OR REPLACE VIEW vw_anomaly_by_meter AS
SELECT
    meter_id,
    COUNT(*) FILTER (WHERE anomaly_flag = 1) AS anomaly_count,
    AVG(anomaly_score)                       AS avg_anomaly_score,
    MAX(energy_consumption)                  AS max_anomalous_consumption
FROM fact_anomalies
WHERE anomaly_flag = 1
GROUP BY meter_id
ORDER BY anomaly_count DESC;

CREATE OR REPLACE VIEW vw_prediction_accuracy AS
SELECT
    model_name,
    model_version,
    COUNT(*)                        AS prediction_count,
    AVG(ABS(prediction_error))      AS mae,
    SQRT(AVG(POWER(prediction_error, 2))) AS rmse,
    AVG(abs_percentage_error)       AS mape
FROM fact_predictions
WHERE actual_consumption IS NOT NULL
GROUP BY model_name, model_version;

CREATE OR REPLACE VIEW vw_actual_vs_predicted AS
SELECT
    reading_ts,
    meter_id,
    actual_consumption,
    predicted_consumption,
    prediction_error,
    abs_percentage_error,
    model_name
FROM fact_predictions
ORDER BY reading_ts;
