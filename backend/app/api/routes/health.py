"""
api/routes/health.py
======================

PatientTriage.ai — Health Check Endpoint
--------------------------------------------
Simple liveness/readiness endpoint. Used by Docker Compose healthchecks
and the frontend's connectivity indicator. Deliberately contains no
clinical logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging_config import get_logger
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Report application liveness and database connectivity.

    Returns
    -------
    HealthResponse
        `status="ok"` with `database_reachable=True` when a trivial
        `SELECT 1` succeeds against the configured database.
    """
    settings = get_settings()

    try:
        db.execute(text("SELECT 1"))
        database_reachable = True
    except Exception as exc:  # noqa: BLE001 — health check must never raise
        logger.error("Health check database probe failed: %s", exc)
        database_reachable = False

    return HealthResponse(
        status="ok" if database_reachable else "degraded",
        environment=settings.ENVIRONMENT,
        project_name=settings.PROJECT_NAME,
        database_reachable=database_reachable,
    )
