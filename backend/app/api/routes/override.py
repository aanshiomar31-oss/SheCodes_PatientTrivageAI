"""
api/routes/override.py
=========================

PatientTriage.ai — Nurse Override
----------------------------------------
POST /api/v1/override

Enforcement point for "the nurse decides": this endpoint never edits or
removes the AI's recommendation — it records a new, separate,
attributed event alongside it. `GET /queue` shows the override's
`new_priority` as the patient's active priority while still reporting
`recommended_priority` and `overridden=true`, so the AI's original
recommendation stays visible, not replaced.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.audit_log import AuditLog
from app.models.triage_stay import TriageStay
from app.services.cps import format_patient_id
from app.websocket.connection_manager import manager

router = APIRouter(prefix="/override", tags=["override"])
logger = get_logger(__name__)


class OverrideRequest(BaseModel):
    stay_id: int
    original_priority: str = Field(pattern="^P[1-5]$")
    new_priority: str = Field(pattern="^P[1-5]$")
    reason: str = Field(min_length=3, max_length=1000, description="Mandatory — an override with no reason is rejected.")
    actor: str = Field(default="nurse", max_length=128)


@router.post("")
async def create_override(body: OverrideRequest, db: Session = Depends(get_db)) -> dict:
    """Record a clinician override and broadcast it over the WebSocket."""
    stay = db.get(TriageStay, body.stay_id)
    if stay is None:
        raise HTTPException(status_code=404, detail=f"No triage stay with stay_id={body.stay_id}")

    entry = AuditLog(
        event_type="recommendation_overridden",
        actor=body.actor,
        resource_type="triage_stay",
        resource_id=str(body.stay_id),
        details=json.dumps({
            "original_priority": body.original_priority,
            "new_priority": body.new_priority,
            "reason": body.reason,
        }),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info("Override recorded: stay_id=%s %s -> %s by %s",
                body.stay_id, body.original_priority, body.new_priority, body.actor)

    await manager.broadcast({
        "event": "override",
        "patient_id": format_patient_id(body.stay_id),
        "stay_id": body.stay_id,
        "original_priority": body.original_priority,
        "new_priority": body.new_priority,
        "reason": body.reason,
        "actor": body.actor,
    })

    return {
        "audit_id": entry.id,
        "stay_id": body.stay_id,
        "original_priority": body.original_priority,
        "new_priority": body.new_priority,
        "recorded_at": entry.created_at.isoformat(),
    }
