"""
api/routes/vitals.py
=======================

PatientTriage.ai — Vitals Update
------------------------------------
POST /api/v1/vitals/update

When vitals worsen, re-run the rule engine and ensemble, generate a new
recommendation, and broadcast an alert. This endpoint NEVER changes
queue order by itself — see `create_override` in `override.py` for the
only path that changes a patient's active priority. Worsened vitals
here only ever produce a RECOMMENDATION to reassess, surfaced via the
WebSocket, which a nurse must act on explicitly.

Limitation stated rather than hidden: `TriageStay` stores one
point-in-time vitals snapshot per stay, not a time series. This
endpoint overwrites the current vitals and logs the previous values to
the audit trail so a trend is reconstructable from audit history, but
there is no dedicated vitals-history table — a real trend view would
need a new table and migration, intentionally not added silently here.
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
from app.services.cps import compute_cps, format_patient_id
from app.websocket.connection_manager import manager
from ml.predict import predict

router = APIRouter(prefix="/vitals", tags=["vitals"])
logger = get_logger(__name__)

VITALS_FIELDS = ("heart_rate", "resp_rate", "sbp", "dbp", "temperature", "o2_sat", "pain")


class VitalsUpdateRequest(BaseModel):
    stay_id: int
    heart_rate: float | None = None
    resp_rate: float | None = None
    sbp: float | None = None
    dbp: float | None = None
    temperature: float | None = None
    o2_sat: float | None = None
    pain: float | None = None
    actor: str = Field(default="nurse", max_length=128)


def _stay_to_patient_dict(stay: TriageStay) -> dict:
    return {
        "age": None,
        "gender": stay.gender,
        "heartrate": stay.heart_rate,
        "resprate": stay.resp_rate,
        "sbp": stay.sbp,
        "dbp": stay.dbp,
        "temperature": stay.temperature,
        "o2sat": stay.o2_sat,
        "pain": stay.pain,
        "chief_complaint": stay.chief_complaint,
        "arrival_transport": stay.arrival_transport,
        "night_shift_flag": stay.night_shift_flag,
        "weekend_flag": stay.weekend_flag,
        "arrival_hour": stay.arrival_hour,
    }


@router.post("/update")
async def update_vitals(body: VitalsUpdateRequest, db: Session = Depends(get_db)) -> dict:
    """Update a stay's vitals, re-score, and broadcast a reassessment alert."""
    stay = db.get(TriageStay, body.stay_id)
    if stay is None:
        raise HTTPException(status_code=404, detail=f"No triage stay with stay_id={body.stay_id}")

    previous = {f: getattr(stay, f) for f in VITALS_FIELDS}
    previous_patient = _stay_to_patient_dict(stay)
    try:
        previous_rec = predict(previous_patient)
    except Exception:  # noqa: BLE001 — comparison is best-effort, must not block the update
        previous_rec = None

    for field in VITALS_FIELDS:
        value = getattr(body, field)
        if value is not None:
            setattr(stay, field, value)

    db.add(AuditLog(
        event_type="vitals_updated",
        actor=body.actor,
        resource_type="triage_stay",
        resource_id=str(body.stay_id),
        details=json.dumps({"previous": previous, "new": {f: getattr(stay, f) for f in VITALS_FIELDS}}),
    ))
    db.commit()
    db.refresh(stay)

    rec = predict(_stay_to_patient_dict(stay))
    cps_info = compute_cps(stay, rec)
    worsened = previous_rec is not None and rec["risk_score"] > previous_rec["risk_score"]

    await manager.broadcast({
        "event": "vitals_updated",
        "patient_id": format_patient_id(body.stay_id),
        "stay_id": body.stay_id,
        "priority": rec["priority"],
        "risk_score": rec["risk_score"],
        "clinical_priority_score": cps_info["cps_100"],
        "worsened": worsened,
        "escalated": rec["escalated"],
        "message": (
            f"Patient {format_patient_id(body.stay_id)} vitals updated — recommend reassessment."
            if worsened else f"Patient {format_patient_id(body.stay_id)} vitals updated."
        ),
    })

    return {
        "stay_id": body.stay_id,
        "patient_id": format_patient_id(body.stay_id),
        "worsened": worsened,
        "recommendation": {**rec, "clinical_priority_score": cps_info["cps_100"]},
    }
