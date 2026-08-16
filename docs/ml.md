# Machine Learning

## Feature engineering (`src/ml/feature_engineering.py`)

* Electrical: voltage, current, power factor.
* Weather: temperature, humidity, weather condition, temperature band.
* Calendar: hour, day, month, day of week, weekend and peak-hour flags, season.
* History (per meter, timestamp-ordered): lags 1h/2h/3h/24h, rolling mean and std over 3h/24h.
* Cyclical encodings for hour, month and day of week; one-hot for categoricals.

38 features total. Rows lacking sufficient history are dropped rather than back-filled.

## Split

`time_series_split` takes the last 20% of the chronologically sorted data as the test set — no
random shuffling, so no future leakage.

## Models and selection

Linear Regression, Random Forest Regressor and Gradient Boosting Regressor are trained on the
same matrix and scored on MAE, MSE, RMSE and R². The lowest-RMSE model wins and is persisted with
its feature list and metadata to `models/best_model.joblib`; all scores go to
`models/model_metrics.json`.

| Model | MAE | MSE | RMSE | R² |
| --- | --- | --- | --- | --- |
| **Linear Regression (selected)** | **0.2460** | **1.4199** | **1.1916** | **0.8758** |
| Random Forest | 0.2609 | 1.5905 | 1.2612 | 0.8609 |
| Gradient Boosting | 0.2701 | 1.5442 | 1.2427 | 0.8649 |

Linear Regression wins because the generator's consumption signal is largely additive in the
lag, calendar and weather features; the tree ensembles slightly overfit the noise band.

## Prediction

`predict_frame` scores a DataFrame; `predict_single` rebuilds lag/rolling features from the
meter's recent history so the API can score an arbitrary new input. Output columns: actual,
predicted, error, model name.

## Anomaly detection

* **Robust z-score** per meter and hour-of-day (median/MAD) → `sudden_spike`,
  `high_consumption`, `low_consumption`.
* **Isolation Forest** over consumption, voltage, current, power factor, temperature and
  humidity → `abnormal_behaviour`.

Severity is derived from the score magnitude (`low`/`medium`/`high`). Results are written to Gold
and `fact_anomalies`.

## Retraining

`python -m src.ml.train` (optionally `--sample-rows`) → `python -m src.ml.predict` →
`python -m src.ml.anomaly_detection` → `python -m src.etl.gold_powerbi`.
