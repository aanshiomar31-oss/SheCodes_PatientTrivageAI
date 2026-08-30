"""
schemas/health.py
===================

PatientTriage.ai — Health Check Schemas
------------------------------------------
Response models for the `/health` and `/` endpoints used by orchestration
tooling (Docker healthchecks, uptime monitors, the frontend's connectivity
check) to verify the API is alive.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for `GET /api/v1/health`."""

    status: str = Field(..., examples=["ok"])
    environment: str = Field(..., examples=["development"])
    project_name: str = Field(..., examples=["PatientTriage.ai"])
    database_reachable: bool = Field(
        ..., description="Whether a trivial query against the configured database succeeded."
    )


class RootResponse(BaseModel):
    """Response body for `GET /`."""

    message: str
    docs_url: str
    governing_rule: str = "The AI recommends. The nurse decides."
