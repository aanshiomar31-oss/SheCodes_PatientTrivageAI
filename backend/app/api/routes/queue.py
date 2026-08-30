"""
api/routes/queue.py
=======================

PatientTriage.ai — Live Queue
----------------------------------
GET /api/v1/queue

Live view over `triage_stays`, covering both the pre-loaded MIMIC-IV-ED
cohort and any patients created live via `POST /triage`
(see `app/services/patient_registry.py`).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.audit_log import AuditLog
from app.models.triage_stay import TriageStay
from app.services.cps import compute_cps, format_patient_id
from ml.predict import predict

router = APIRouter(prefix="/queue", tags=["queue"])
logger = get_logger(__name__)


def _stay_to_patient_dict(stay: TriageStay) -> dict:
    return {
        "age": None,  # no source age data in this MIMIC-IV-ED extract; live-intake age is not persisted either
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


class QueueEntry(BaseModel):
    stay_id: int
    patient_id: str
    chief_complaint: str | None
    priority: str
    recommended_priority: str
    overridden: bool
    risk_score: int
    confidence: float
    uncertainty_reason: str | None
    escalated: bool
    cps: float
    cps_components: dict
    waited_minutes: float
    status: str = Field(description="'waiting' for every entry currently — see module docstring for scope.")


class QueueResponse(BaseModel):
    count: int
    order: str
    entries: list[QueueEntry]


@router.get("", response_model=QueueResponse)
def list_queue(
    sort: str = Query(
        "priority", pattern="^(arrival|cps|priority)$",
        description="'priority' (default: priority, then CPS, then arrival — see docstring), "
                    "'arrival' (canonical insertion order), or 'cps' (recommended-order preview).",
    ),
    db: Session = Depends(get_db),
) -> QueueResponse:
    """
    Live queue view.

    Governing rule enforcement: the AI never silently reorders the
    queue. `sort=priority` returns patients ordered by priority level,
    then Clinical Priority Score, then arrival time — this is a
    RECOMMENDED ORDER FOR DISPLAY, computed fresh on every request, not
    a stored/mutated field on any patient record. `sort=arrival` shows
    the queue's raw insertion order, unaffected by any recommendation,
    for a nurse who wants to see intake order specifically. `sort=cps`
    is the same recommended order, CPS-only, kept for direct CPS
    inspection. No option here writes anything or changes what
    `priority` a patient is actually holding — that only happens
    through `POST /override`.
    """
    stays = db.execute(select(TriageStay)).scalars().all()

    override_rows = db.execute(
        select(AuditLog).where(
            AuditLog.event_type == "recommendation_overridden",
            AuditLog.resource_type == "triage_stay",
        ).order_by(AuditLog.created_at.asc())
    ).scalars().all()
    latest_override: dict[str, str] = {}
    for row in override_rows:
        try:
            latest_override[row.resource_id] = json.loads(row.details)["new_priority"]
        except Exception:  # noqa: BLE001 — a malformed historical row must not break the queue
            continue

    entries = []
    for stay in stays:
        patient = _stay_to_patient_dict(stay)
        try:
            rec = predict(patient)
        except Exception as exc:  # noqa: BLE001 — one bad row must not blank the whole queue
            logger.error("predict() failed for stay_id=%s: %s", stay.stay_id, exc)
            continue

        cps_info = compute_cps(stay, rec)
        override_priority = latest_override.get(str(stay.stay_id))

        entries.append(QueueEntry(
            stay_id=stay.stay_id,
            patient_id=format_patient_id(stay.stay_id),
            chief_complaint=stay.chief_complaint,
            priority=override_priority or rec["priority"],
            recommended_priority=rec["priority"],
            overridden=override_priority is not None,
            risk_score=rec["risk_score"],
            confidence=rec["confidence"],
            uncertainty_reason=rec["uncertainty_reason"],
            escalated=rec["escalated"],
            cps=cps_info["cps"],
            cps_components=cps_info["components"],
            waited_minutes=cps_info["waited_minutes"],
            status="waiting",
        ))

    priority_rank = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}
    if sort == "cps":
        entries.sort(key=lambda e: -e.cps)
    elif sort == "priority":
        entries.sort(key=lambda e: (priority_rank.get(e.priority, 5), -e.cps, -e.waited_minutes))
    else:
        entries.sort(key=lambda e: e.stay_id)

    return QueueResponse(count=len(entries), order=sort, entries=entries)
