"""
tests/test_triage.py
=======================

Tests for `POST /api/v1/triage`. Uses the same `test_client` fixture as
`test_health.py` (in-memory SQLite, never the dev database). These tests
depend on a trained ensemble existing at `backend/reports/triage_ensemble.joblib`
— run `python -m ml.train_model` first if they fail with "no trained model".
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_empty_request_rejected(test_client: TestClient) -> None:
    """An empty request must be rejected, never silently scored as a well adult."""
    response = test_client.post("/api/v1/triage", json={})
    assert response.status_code == 422


def test_critical_hypoxia_escalates_to_p1(test_client: TestClient) -> None:
    """SpO2 < 90 is a rule-engine red flag and must clamp to P1 regardless of the ensemble."""
    response = test_client.post("/api/v1/triage", json={
        "age": 72, "gender": "F", "heartrate": 118, "sbp": 92, "dbp": 60,
        "resprate": 28, "temperature": 38.8, "o2sat": 89, "pain": 5,
        "chief_complaint": "Chest discomfort",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "P1"
    assert body["escalated"] is True
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["top_features"]) > 0
    assert body["governing_rule"] == "The AI recommends. The nurse decides."


def test_well_patient_not_escalated(test_client: TestClient) -> None:
    """A patient with normal vitals and no red flag must not be escalated."""
    response = test_client.post("/api/v1/triage", json={
        "age": 28, "gender": "M", "heartrate": 74, "sbp": 118, "dbp": 76,
        "resprate": 15, "temperature": 98.2, "o2sat": 99, "pain": 1,
        "chief_complaint": "Minor ankle sprain",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["priority"] in ("P3", "P4", "P5")


def test_missing_vitals_reduce_confidence_not_silently_normal(test_client: TestClient) -> None:
    """A near-empty record must lower confidence and name the gap, never read as 'normal'."""
    response = test_client.post("/api/v1/triage", json={"heartrate": 105})
    assert response.status_code == 200
    body = response.json()
    assert body["uncertainty_reason"] is not None
    assert "not recorded" in body["uncertainty_reason"].lower()


def test_recommendation_is_persisted(test_client: TestClient) -> None:
    """Every recommendation must be reviewable — a prediction_id confirms it was audit-logged."""
    response = test_client.post("/api/v1/triage", json={
        "age": 40, "heartrate": 88, "sbp": 122, "dbp": 80, "chief_complaint": "Headache",
    })
    assert response.status_code == 200
    assert response.json()["prediction_id"] is not None
