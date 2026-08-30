"""
tests/test_workflow.py
=========================

Tests the full live workflow this platform's frontend depends on:
intake -> appears in queue -> override -> vitals update -> audit trail,
plus the WebSocket broadcasts each write triggers. Uses the same
`test_client` fixture as test_health.py / test_triage.py (in-memory
SQLite). Depends on a trained ensemble existing — run
`python -m ml.train_model` first if these fail with "no trained model".
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _receive_until(ws, event_name: str, max_tries: int = 15):
    """The live feed carries multiple independent broadcasters (intake,
    override, vitals, and the background monitor) on one socket — a
    client must dispatch by event type, never assume strict
    request/response ordering. This helper does the same filtering a
    real frontend client does."""
    for _ in range(max_tries):
        msg = ws.receive_json()
        if msg.get("event") == event_name:
            return msg
    return None


def test_intake_creates_a_queue_entry(test_client: TestClient) -> None:
    """A submitted patient must actually appear in GET /queue, not just get a response."""
    r = test_client.post("/api/v1/triage", json={
        "age": 50, "heartrate": 88, "sbp": 122, "chief_complaint": "Workflow test patient",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["patient_id"].startswith("ED")
    assert 0 <= body["clinical_priority_score"] <= 100

    queue = test_client.get("/api/v1/queue").json()
    match = [e for e in queue["entries"] if e["patient_id"] == body["patient_id"]]
    assert len(match) == 1
    assert match[0]["chief_complaint"] == "Workflow test patient"


def test_override_then_vitals_then_audit_trail(test_client: TestClient) -> None:
    """The full nurse workflow: override a recommendation, update vitals, review the audit trail."""
    intake = test_client.post("/api/v1/triage", json={
        "age": 60, "heartrate": 90, "sbp": 130, "chief_complaint": "Audit trail test",
    }).json()
    stay_id = None
    # stay_id isn't in the /triage response; recover it via the queue.
    queue = test_client.get("/api/v1/queue").json()
    stay_id = next(e["stay_id"] for e in queue["entries"] if e["patient_id"] == intake["patient_id"])

    override = test_client.post("/api/v1/override", json={
        "stay_id": stay_id, "original_priority": intake["priority"],
        "new_priority": "P2", "reason": "Nurse clinical judgement",
    })
    assert override.status_code == 200

    queue_after = test_client.get("/api/v1/queue").json()
    entry = next(e for e in queue_after["entries"] if e["stay_id"] == stay_id)
    assert entry["priority"] == "P2"
    assert entry["overridden"] is True
    assert entry["recommended_priority"] == intake["priority"]  # AI's original recommendation still visible

    vitals = test_client.post("/api/v1/vitals/update", json={
        "stay_id": stay_id, "heart_rate": 145, "o2_sat": 86,
    })
    assert vitals.status_code == 200
    assert vitals.json()["worsened"] is True

    audit = test_client.get("/api/v1/audit", params={"patient_id": stay_id}).json()
    event_types = {e["event_type"] for e in audit["entries"]}
    assert {"triage_recommendation", "recommendation_overridden", "vitals_updated"} <= event_types
    assert all(e["patient_id"] == intake["patient_id"] for e in audit["entries"])


def test_override_requires_a_reason(test_client: TestClient) -> None:
    intake = test_client.post("/api/v1/triage", json={"age": 40, "heartrate": 80, "sbp": 118}).json()
    queue = test_client.get("/api/v1/queue").json()
    stay_id = next(e["stay_id"] for e in queue["entries"] if e["patient_id"] == intake["patient_id"])

    r = test_client.post("/api/v1/override", json={
        "stay_id": stay_id, "original_priority": intake["priority"], "new_priority": "P1", "reason": "",
    })
    assert r.status_code == 422


def test_websocket_broadcasts_intake_override_and_vitals(test_client: TestClient) -> None:
    """The three write endpoints each broadcast their event, dispatched by type over one shared socket."""
    with test_client.websocket_connect("/ws/live") as ws:
        ack = ws.receive_json()
        assert ack["event"] == "connection_ack"

        test_client.post("/api/v1/triage", json={
            "age": 35, "heartrate": 92, "sbp": 124, "chief_complaint": "WebSocket test",
        })
        new_patient = _receive_until(ws, "new_patient")
        assert new_patient is not None
        stay_id = new_patient["stay_id"]

        test_client.post("/api/v1/override", json={
            "stay_id": stay_id, "original_priority": new_patient["priority"],
            "new_priority": "P4", "reason": "WebSocket broadcast test",
        })
        override_event = _receive_until(ws, "override")
        assert override_event is not None
        assert override_event["new_priority"] == "P4"

        test_client.post("/api/v1/vitals/update", json={"stay_id": stay_id, "heart_rate": 130})
        vitals_event = _receive_until(ws, "vitals_updated")
        assert vitals_event is not None
        assert vitals_event["stay_id"] == stay_id
