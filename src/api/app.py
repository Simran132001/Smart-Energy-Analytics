"""Flask REST API exposing the Smart Energy warehouse and ML model."""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request

from src.db.postgres import healthcheck, read_sql
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_LIMIT = 5000


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.to_dict(orient="records")


def _limit(default: int = 100) -> int:
    try:
        value = int(request.args.get("limit", default))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    if value < 1 or value > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    return value


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        logger.warning("Bad request: %s", error)
        return jsonify({"error": "bad_request", "message": str(error)}), 400

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": "not_found", "message": "Unknown endpoint"}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        logger.exception("Unhandled error: %s", error)
        return jsonify({"error": "internal_server_error", "message": str(error)}), 500

    @app.get("/health")
    def health():
        model_loaded = False
        try:
            from src.ml.predict import load_model

            load_model()
            model_loaded = True
        except Exception as exc:  # noqa: BLE001 - health must always answer
            logger.warning("Model not loadable: %s", exc)

        database_ok = healthcheck()
        status = "healthy" if database_ok and model_loaded else "degraded"
        return jsonify(
            {
                "status": status,
                "database": "up" if database_ok else "down",
                "model_loaded": model_loaded,
                "version": os.getenv("APP_VERSION", "1.0.0"),
            }
        ), (200 if status == "healthy" else 503)

    @app.get("/api/energy/summary")
    def energy_summary():
        summary = read_sql("SELECT * FROM vw_energy_summary")
        anomalies = read_sql("SELECT COUNT(*) AS total_anomalies FROM fact_anomalies WHERE anomaly_flag = 1")
        payload = _records(summary)[0] if not summary.empty else {}
        payload["total_anomalies"] = int(anomalies.iloc[0]["total_anomalies"]) if not anomalies.empty else 0
        return jsonify({"data": payload}), 200

    @app.get("/api/energy/daily")
    def energy_daily():
        limit = _limit(90)
        meter_id = request.args.get("meter_id")
        if meter_id:
            df = read_sql(
                "SELECT date_key, meter_id, total_consumption, avg_consumption, max_consumption, "
                "min_consumption, avg_temperature FROM fact_daily_consumption "
                "WHERE meter_id = :meter_id ORDER BY date_key DESC LIMIT :limit",
                {"meter_id": meter_id, "limit": limit},
            )
        else:
            df = read_sql(
                "SELECT * FROM vw_daily_trend ORDER BY date_key DESC LIMIT :limit", {"limit": limit}
            )
        return jsonify({"count": len(df), "data": _records(df)}), 200

    @app.get("/api/energy/monthly")
    def energy_monthly():
        df = read_sql("SELECT * FROM vw_monthly_trend")
        return jsonify({"count": len(df), "data": _records(df)}), 200

    @app.get("/api/energy/hourly")
    def energy_hourly():
        df = read_sql("SELECT * FROM vw_hourly_pattern")
        return jsonify({"count": len(df), "data": _records(df)}), 200

    @app.get("/api/meters")
    def meters():
        df = read_sql("SELECT * FROM vw_meter_ranking")
        return jsonify({"count": len(df), "data": _records(df)}), 200

    @app.get("/api/meters/<meter_id>")
    def meter_detail(meter_id: str):
        df = read_sql(
            "SELECT * FROM vw_meter_ranking WHERE meter_id = :meter_id", {"meter_id": meter_id}
        )
        if df.empty:
            return jsonify({"error": "not_found", "message": f"Unknown meter {meter_id}"}), 404
        return jsonify({"data": _records(df)[0]}), 200

    @app.get("/api/anomalies")
    def anomalies():
        limit = _limit(100)
        meter_id = request.args.get("meter_id")
        severity = request.args.get("severity")
        query = (
            "SELECT reading_ts, meter_id, energy_consumption, anomaly_flag, anomaly_type, "
            "anomaly_score, anomaly_severity, detection_method FROM fact_anomalies WHERE anomaly_flag = 1"
        )
        params: dict[str, Any] = {"limit": limit}
        if meter_id:
            query += " AND meter_id = :meter_id"
            params["meter_id"] = meter_id
        if severity:
            if severity not in {"low", "medium", "high"}:
                raise ValueError("severity must be one of low, medium, high")
            query += " AND anomaly_severity = :severity"
            params["severity"] = severity
        query += " ORDER BY reading_ts DESC LIMIT :limit"
        df = read_sql(query, params)
        return jsonify({"count": len(df), "data": _records(df)}), 200

    @app.get("/api/predictions")
    def predictions():
        limit = _limit(100)
        meter_id = request.args.get("meter_id")
        query = "SELECT * FROM vw_actual_vs_predicted"
        params: dict[str, Any] = {"limit": limit}
        if meter_id:
            query = (
                "SELECT reading_ts, meter_id, actual_consumption, predicted_consumption, "
                "prediction_error, abs_percentage_error, model_name FROM fact_predictions "
                "WHERE meter_id = :meter_id"
            )
            params["meter_id"] = meter_id
        query += " ORDER BY reading_ts DESC LIMIT :limit"
        df = read_sql(query, params)
        accuracy = read_sql("SELECT * FROM vw_prediction_accuracy")
        return jsonify(
            {"count": len(df), "accuracy": _records(accuracy), "data": _records(df)}
        ), 200

    @app.post("/api/predict")
    def predict():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")

        required = ["timestamp", "meter_id", "temperature", "humidity"]
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        for numeric_field in ("temperature", "humidity", "voltage", "current", "power_factor"):
            if numeric_field in payload and not isinstance(payload[numeric_field], (int, float)):
                raise ValueError(f"{numeric_field} must be numeric")

        from src.ml.predict import predict_single

        try:
            result = predict_single(payload)
        except ValueError as exc:
            return jsonify({"error": "bad_request", "message": str(exc)}), 400
        return jsonify({"data": result}), 200

    logger.info("Flask application initialised")
    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_ENV") == "development",
    )
