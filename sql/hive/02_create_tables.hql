USE smart_energy;

-- Bronze: raw typed smart-meter readings, partitioned by event date
CREATE EXTERNAL TABLE IF NOT EXISTS bronze_energy_readings (
    meter_id              STRING,
    meter_type            STRING,
    region                STRING,
    `timestamp`           TIMESTAMP,
    energy_consumption    DOUBLE,
    voltage               DOUBLE,
    current               DOUBLE,
    power_factor          DOUBLE,
    temperature           DOUBLE,
    humidity              DOUBLE,
    weather_condition     STRING,
    is_peak_hour          INT,
    tariff_period         STRING,
    hvac_kwh              DOUBLE,
    lighting_kwh          DOUBLE,
    appliance_kwh         DOUBLE,
    injected_anomaly      INT,
    injected_anomaly_type STRING,
    season                STRING,
    ingestion_ts          TIMESTAMP,
    source_system         STRING
)
PARTITIONED BY (event_date DATE)
STORED AS PARQUET
LOCATION '/smart_energy/bronze/energy_readings';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_meter_info (
    meter_id          STRING,
    meter_type        STRING,
    region            STRING,
    installation_date STRING,
    rated_voltage     DOUBLE,
    base_load_kwh     DOUBLE
)
STORED AS PARQUET
LOCATION '/smart_energy/bronze/meter_info';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_weather (
    `timestamp`       TIMESTAMP,
    temperature       DOUBLE,
    humidity          DOUBLE,
    weather_condition STRING
)
STORED AS PARQUET
LOCATION '/smart_energy/bronze/weather';

-- Silver: cleaned and enriched readings
CREATE EXTERNAL TABLE IF NOT EXISTS silver_energy_readings (
    meter_id           STRING,
    meter_type         STRING,
    region             STRING,
    `timestamp`        TIMESTAMP,
    energy_consumption DOUBLE,
    voltage            DOUBLE,
    current            DOUBLE,
    power_factor       DOUBLE,
    temperature        DOUBLE,
    humidity           DOUBLE,
    weather_condition  STRING,
    temperature_band   STRING,
    `year`             INT,
    `month`            INT,
    `day`              INT,
    `hour`             INT,
    `minute`           INT,
    day_of_week        INT,
    weekend_flag       INT,
    peak_hour_flag     INT,
    season             STRING,
    hvac_kwh           DOUBLE,
    lighting_kwh       DOUBLE,
    appliance_kwh      DOUBLE
)
PARTITIONED BY (`date` DATE)
STORED AS PARQUET
LOCATION '/smart_energy/silver/energy_readings';

MSCK REPAIR TABLE bronze_energy_readings;
MSCK REPAIR TABLE silver_energy_readings;
