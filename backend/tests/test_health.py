"""
tests/test_health.py
======================

Smoke tests for the foundational endpoints shipped in this milestone.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_endpoint(test_client: TestClient) -> None:
    """The root endpoint should confirm the API is running."""
    response = test_client.get("/")
    assert response.status_code == 200

    body = response.json()
    assert body["message"].startswith("PatientTriage.ai")
    assert body["docs_url"] == "/docs"
    assert body["governing_rule"] == "The AI recommends. The nurse decides."


def test_health_endpoint(test_client: TestClient) -> None:
    """The health endpoint should report ok status and DB reachability."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database_reachable"] is True
    assert body["project_name"] == "PatientTriage.ai"


def test_docs_available(test_client: TestClient) -> None:
    """Swagger UI should be reachable for API exploration."""
    response = test_client.get("/docs")
    assert response.status_code == 200
