USE smart_energy;

CREATE EXTERNAL TABLE IF NOT EXISTS gold_hourly_consumption (
    `date`              DATE,
    `hour`              INT,
    meter_id            STRING,
    total_consumption   DOUBLE,
    avg_consumption     DOUBLE,
    max_consumption     DOUBLE,
    min_consumption     DOUBLE,
    reading_count       BIGINT,
    avg_temperature     DOUBLE,
    peak_hour_flag      INT
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/hourly_consumption';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_daily_consumption (
    `date`            DATE,
    meter_id          STRING,
    total_consumption DOUBLE,
    avg_consumption   DOUBLE,
    max_consumption   DOUBLE,
    min_consumption   DOUBLE,
    reading_count     BIGINT,
    avg_temperature   DOUBLE,
    weekend_flag      INT,
    season            STRING
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/daily_consumption';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_monthly_consumption (
    `year`            INT,
    `month`           INT,
    meter_id          STRING,
    total_consumption DOUBLE,
    avg_consumption   DOUBLE,
    max_consumption   DOUBLE,
    min_consumption   DOUBLE,
    reading_count     BIGINT
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/monthly_consumption';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_meter_consumption (
    meter_id           STRING,
    meter_type         STRING,
    region             STRING,
    total_consumption  DOUBLE,
    avg_consumption    DOUBLE,
    max_consumption    DOUBLE,
    min_consumption    DOUBLE,
    reading_count      BIGINT,
    consumption_rank   INT
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/meter_consumption';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_peak_offpeak_consumption (
    `date`            DATE,
    tariff_period     STRING,
    total_consumption DOUBLE,
    avg_consumption   DOUBLE,
    reading_count     BIGINT
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/peak_offpeak_consumption';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_weather_energy (
    `date`             DATE,
    weather_condition  STRING,
    temperature_band   STRING,
    avg_temperature    DOUBLE,
    avg_humidity       DOUBLE,
    total_consumption  DOUBLE,
    avg_consumption    DOUBLE,
    reading_count      BIGINT
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/weather_energy';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_predictions (
    `timestamp`            TIMESTAMP,
    meter_id               STRING,
    actual_consumption     DOUBLE,
    predicted_consumption  DOUBLE,
    prediction_error       DOUBLE,
    abs_percentage_error   DOUBLE,
    model_name             STRING,
    model_version          STRING
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/predictions';

CREATE EXTERNAL TABLE IF NOT EXISTS gold_anomalies (
    `timestamp`        TIMESTAMP,
    meter_id           STRING,
    energy_consumption DOUBLE,
    anomaly_flag       INT,
    anomaly_type       STRING,
    anomaly_score      DOUBLE,
    anomaly_severity   STRING,
    detection_method   STRING
)
STORED AS PARQUET
LOCATION '/smart_energy/gold/anomalies';
