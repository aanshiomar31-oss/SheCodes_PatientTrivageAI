"""
api/routes/audit.py
=======================

PatientTriage.ai — Audit Log
----------------------------------
GET /api/v1/audit

Chronological history of AI recommendations, nurse overrides, and
vitals updates. Every entry is append-only (see `AuditLog` model
docstring) and attributed to an actor and timestamp.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.services.cps import format_patient_id

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    patient_id: int | None = Query(None, description="Filter to a single stay_id."),
    event_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict:
    """List audit log entries, most recent first, optionally filtered by patient or event type."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if patient_id is not None:
        stmt = stmt.where(AuditLog.resource_id == str(patient_id))
    if event_type is not None:
        stmt = stmt.where(AuditLog.event_type == event_type)

    rows = db.execute(stmt).scalars().all()
    return {
        "count": len(rows),
        "entries": [
            {
                "id": r.id,
                "event_type": r.event_type,
                "actor": r.actor,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "patient_id": format_patient_id(int(r.resource_id)) if r.resource_id.isdigit() else r.resource_id,
                "details": json.loads(r.details) if r.details else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
