"""Flask API tests."""
from __future__ import annotations

import pytest

from tests.conftest import requires_db, requires_model


def test_health_endpoint_always_answers(api_client):
    response = api_client.get("/health")
    assert response.status_code in (200, 503)
    payload = response.get_json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "database" in payload and "model_loaded" in payload


def test_unknown_endpoint_returns_404(api_client):
    response = api_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_predict_requires_json_body(api_client):
    response = api_client.post("/api/predict", json={"meter_id": "MTR-001"})
    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["message"]


def test_predict_rejects_non_numeric_temperature(api_client):
    response = api_client.post(
        "/api/predict",
        json={"timestamp": "2024-01-01 10:00:00", "meter_id": "MTR-001", "temperature": "warm", "humidity": 50},
    )
    assert response.status_code == 400


@requires_db
def test_summary_endpoint(api_client):
    response = api_client.get("/api/energy/summary")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["meter_count"] > 0
    assert data["total_consumption"] > 0
    assert "total_anomalies" in data


@requires_db
@pytest.mark.parametrize(
    "endpoint",
    ["/api/energy/daily?limit=5", "/api/energy/monthly", "/api/energy/hourly", "/api/meters"],
)
def test_read_endpoints(api_client, endpoint):
    response = api_client.get(endpoint)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == len(payload["data"])


@requires_db
def test_limit_validation(api_client):
    assert api_client.get("/api/energy/daily?limit=0").status_code == 400
    assert api_client.get("/api/energy/daily?limit=abc").status_code == 400


@requires_db
def test_unknown_meter_returns_404(api_client):
    assert api_client.get("/api/meters/MTR-999").status_code == 404


@requires_db
def test_anomalies_endpoint_filters(api_client):
    response = api_client.get("/api/anomalies?limit=10&severity=high")
    assert response.status_code == 200
    for row in response.get_json()["data"]:
        assert row["anomaly_severity"] == "high"
    assert api_client.get("/api/anomalies?severity=extreme").status_code == 400


@requires_db
def test_predictions_endpoint_reports_accuracy(api_client):
    response = api_client.get("/api/predictions?limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) <= 5
    assert isinstance(payload["accuracy"], list)


@requires_db
@requires_model
def test_predict_endpoint_returns_prediction(api_client):
    response = api_client.post(
        "/api/predict",
        json={"timestamp": "2024-01-05 18:00:00", "meter_id": "MTR-001", "temperature": 8.0, "humidity": 70.0},
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["predicted_consumption"] > 0
    assert data["meter_id"] == "MTR-001"
