-- Smart Energy Analytics - PostgreSQL warehouse schema
CREATE SCHEMA IF NOT EXISTS energy;
SET search_path TO energy, public;

CREATE TABLE IF NOT EXISTS dim_meter (
    meter_id          VARCHAR(16) PRIMARY KEY,
    meter_type        VARCHAR(32)  NOT NULL,
    region            VARCHAR(32)  NOT NULL,
    installation_date DATE,
    rated_voltage     NUMERIC(6, 2) CHECK (rated_voltage > 0),
    base_load_kwh     NUMERIC(10, 4),
    avg_consumption   NUMERIC(12, 4),
    total_consumption NUMERIC(16, 4)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key     DATE PRIMARY KEY,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    month        SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name   VARCHAR(16),
    day          SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL,
    day_name     VARCHAR(16),
    weekend_flag SMALLINT NOT NULL CHECK (weekend_flag IN (0, 1)),
    season       VARCHAR(16) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_hourly_consumption (
    date_key          DATE        NOT NULL REFERENCES dim_date (date_key),
    hour              SMALLINT    NOT NULL CHECK (hour BETWEEN 0 AND 23),
    meter_id          VARCHAR(16) NOT NULL REFERENCES dim_meter (meter_id),
    total_consumption NUMERIC(12, 4) NOT NULL CHECK (total_consumption >= 0),
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    max_consumption   NUMERIC(12, 4) NOT NULL,
    min_consumption   NUMERIC(12, 4) NOT NULL,
    reading_count     INTEGER        NOT NULL,
    avg_temperature   NUMERIC(6, 2),
    peak_hour_flag    SMALLINT       NOT NULL CHECK (peak_hour_flag IN (0, 1)),
    PRIMARY KEY (date_key, hour, meter_id)
);

CREATE TABLE IF NOT EXISTS fact_daily_consumption (
    date_key          DATE        NOT NULL REFERENCES dim_date (date_key),
    meter_id          VARCHAR(16) NOT NULL REFERENCES dim_meter (meter_id),
    total_consumption NUMERIC(12, 4) NOT NULL CHECK (total_consumption >= 0),
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    max_consumption   NUMERIC(12, 4) NOT NULL,
    min_consumption   NUMERIC(12, 4) NOT NULL,
    reading_count     INTEGER        NOT NULL,
    avg_temperature   NUMERIC(6, 2),
    weekend_flag      SMALLINT       NOT NULL,
    season            VARCHAR(16)    NOT NULL,
    PRIMARY KEY (date_key, meter_id)
);

CREATE TABLE IF NOT EXISTS fact_monthly_consumption (
    year              SMALLINT    NOT NULL,
    month             SMALLINT    NOT NULL CHECK (month BETWEEN 1 AND 12),
    meter_id          VARCHAR(16) NOT NULL REFERENCES dim_meter (meter_id),
    total_consumption NUMERIC(14, 4) NOT NULL,
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    max_consumption   NUMERIC(12, 4) NOT NULL,
    min_consumption   NUMERIC(12, 4) NOT NULL,
    reading_count     INTEGER        NOT NULL,
    PRIMARY KEY (year, month, meter_id)
);

CREATE TABLE IF NOT EXISTS fact_peak_offpeak (
    date_key          DATE        NOT NULL REFERENCES dim_date (date_key),
    tariff_period     VARCHAR(16) NOT NULL CHECK (tariff_period IN ('peak', 'off_peak')),
    total_consumption NUMERIC(14, 4) NOT NULL,
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    reading_count     INTEGER        NOT NULL,
    PRIMARY KEY (date_key, tariff_period)
);

CREATE TABLE IF NOT EXISTS fact_weather_energy (
    date_key          DATE        NOT NULL REFERENCES dim_date (date_key),
    weather_condition VARCHAR(32) NOT NULL,
    temperature_band  VARCHAR(16) NOT NULL,
    avg_temperature   NUMERIC(6, 2),
    avg_humidity      NUMERIC(6, 2),
    total_consumption NUMERIC(14, 4) NOT NULL,
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    reading_count     INTEGER        NOT NULL,
    PRIMARY KEY (date_key, weather_condition, temperature_band)
);

CREATE TABLE IF NOT EXISTS fact_meter_consumption (
    meter_id           VARCHAR(16) PRIMARY KEY REFERENCES dim_meter (meter_id),
    meter_type         VARCHAR(32) NOT NULL,
    region             VARCHAR(32) NOT NULL,
    total_consumption  NUMERIC(16, 4) NOT NULL,
    avg_consumption    NUMERIC(12, 4) NOT NULL,
    max_consumption    NUMERIC(12, 4) NOT NULL,
    min_consumption    NUMERIC(12, 4) NOT NULL,
    stddev_consumption NUMERIC(12, 4),
    reading_count      INTEGER        NOT NULL,
    consumption_rank   INTEGER        NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_predictions (
    prediction_id         BIGSERIAL PRIMARY KEY,
    reading_ts            TIMESTAMP   NOT NULL,
    meter_id              VARCHAR(16) NOT NULL REFERENCES dim_meter (meter_id),
    actual_consumption    NUMERIC(12, 4),
    predicted_consumption NUMERIC(12, 4) NOT NULL,
    prediction_error      NUMERIC(12, 4),
    abs_percentage_error  NUMERIC(12, 4),
    model_name            VARCHAR(64) NOT NULL,
    model_version         VARCHAR(32) NOT NULL,
    created_at            TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (reading_ts, meter_id, model_name)
);

CREATE TABLE IF NOT EXISTS fact_anomalies (
    anomaly_id         BIGSERIAL PRIMARY KEY,
    reading_ts         TIMESTAMP   NOT NULL,
    meter_id           VARCHAR(16) NOT NULL REFERENCES dim_meter (meter_id),
    energy_consumption NUMERIC(12, 4) NOT NULL,
    anomaly_flag       SMALLINT    NOT NULL CHECK (anomaly_flag IN (0, 1)),
    anomaly_type       VARCHAR(32) NOT NULL,
    anomaly_score      NUMERIC(12, 4),
    anomaly_severity   VARCHAR(16) NOT NULL,
    detection_method   VARCHAR(32) NOT NULL,
    created_at         TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (reading_ts, meter_id, detection_method)
);

CREATE TABLE IF NOT EXISTS energy_summary (
    summary_id        SERIAL PRIMARY KEY,
    total_consumption NUMERIC(18, 3) NOT NULL,
    avg_consumption   NUMERIC(12, 4) NOT NULL,
    peak_consumption  NUMERIC(12, 4) NOT NULL,
    min_consumption   NUMERIC(12, 4) NOT NULL,
    meter_count       INTEGER        NOT NULL,
    reading_count     BIGINT         NOT NULL,
    period_start      TIMESTAMP      NOT NULL,
    period_end        TIMESTAMP      NOT NULL,
    refreshed_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hourly_meter        ON fact_hourly_consumption (meter_id);
CREATE INDEX IF NOT EXISTS idx_hourly_date         ON fact_hourly_consumption (date_key);
CREATE INDEX IF NOT EXISTS idx_daily_meter         ON fact_daily_consumption (meter_id);
CREATE INDEX IF NOT EXISTS idx_daily_date          ON fact_daily_consumption (date_key);
CREATE INDEX IF NOT EXISTS idx_monthly_meter       ON fact_monthly_consumption (meter_id);
CREATE INDEX IF NOT EXISTS idx_predictions_meter   ON fact_predictions (meter_id, reading_ts);
CREATE INDEX IF NOT EXISTS idx_anomalies_meter     ON fact_anomalies (meter_id, reading_ts);
CREATE INDEX IF NOT EXISTS idx_anomalies_flag      ON fact_anomalies (anomaly_flag);
