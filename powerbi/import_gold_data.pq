// Power Query M - loads every Gold dataset in one step.
// Home > Transform data > Advanced Editor, then set GoldFolder to your local path.
let
    GoldFolder = "C:\\Smart-Energy-Analytics\\data\\gold",

    LoadParquet = (name as text) as table =>
        Parquet.Document(File.Contents(GoldFolder & "\\" & name & ".parquet")),

    powerbi_fact_consumption = LoadParquet("powerbi_fact_consumption"),
    dim_date                 = LoadParquet("dim_date"),
    dim_meter                = LoadParquet("dim_meter"),
    daily_consumption        = LoadParquet("daily_consumption"),
    monthly_consumption      = LoadParquet("monthly_consumption"),
    weekly_consumption       = LoadParquet("weekly_consumption"),
    meter_consumption        = LoadParquet("meter_consumption"),
    peak_offpeak_consumption = LoadParquet("peak_offpeak_consumption"),
    weather_energy           = LoadParquet("weather_energy"),
    predictions              = LoadParquet("predictions"),
    anomalies                = LoadParquet("anomalies"),
    energy_summary           = LoadParquet("energy_summary"),

    Tables = #table(
        {"Name", "Data"},
        {
            {"powerbi_fact_consumption", powerbi_fact_consumption},
            {"dim_date", dim_date},
            {"dim_meter", dim_meter},
            {"daily_consumption", daily_consumption},
            {"monthly_consumption", monthly_consumption},
            {"weekly_consumption", weekly_consumption},
            {"meter_consumption", meter_consumption},
            {"peak_offpeak_consumption", peak_offpeak_consumption},
            {"weather_energy", weather_energy},
            {"predictions", predictions},
            {"anomalies", anomalies},
            {"energy_summary", energy_summary}
        }
    )
in
    Tables

// Live PostgreSQL alternative (Get Data > PostgreSQL database):
//   Server:   localhost:5432      Database: smart_energy
//   Navigator: energy.vw_daily_trend, energy.vw_monthly_trend, energy.vw_hourly_pattern,
//              energy.vw_meter_ranking, energy.vw_peak_offpeak, energy.vw_weather_impact,
//              energy.vw_actual_vs_predicted, energy.vw_anomaly_counts, energy.vw_energy_summary
