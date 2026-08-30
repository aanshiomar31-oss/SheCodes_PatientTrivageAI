"""
api/routes/triage_stays.py
=============================

PatientTriage.ai — Triage Stay Endpoints
----------------------------------------------
Read-only access to `triage_stays` (see `app/models/triage_stay.py`),
the clinically readable ED-stay table loaded from the MIMIC-IV-ED demo
data by `load_triage_stays.py`. Backs the frontend dashboard.

No clinical decision logic lives here — this module returns data and
aggregate counts only. Model recommendations are served from
`api/routes/model.py`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.triage_stay import TriageStay
from app.schemas.triage_stay import TriageStayOut, TriageStayPage, TriageStaySummary

router = APIRouter(prefix="/triage-stays", tags=["triage-stays"])
logger = get_logger(__name__)


@router.get("", response_model=TriageStayPage)
def list_triage_stays(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    acuity: Optional[int] = Query(None, ge=1, le=5, description="Filter to an exact acuity level."),
    age_group: Optional[str] = Query(None, description="Pediatric | Adult | Geriatric | Unknown"),
    untriaged_only: bool = Query(False, description="Only stays with no recorded acuity."),
    high_risk_only: bool = Query(False, description="Only stays the model flagged as high acuity."),
    db: Session = Depends(get_db),
) -> TriageStayPage:
    """
    Paginated, filterable list of ED stays, ordered by acuity (most
    urgent first; untriaged stays — the least certain — sort last, not
    first, since "unknown" must never look like "clear the queue").
    """
    stmt = select(TriageStay)

    if acuity is not None:
        stmt = stmt.where(TriageStay.acuity == acuity)
    if age_group is not None:
        stmt = stmt.where(TriageStay.age_group == age_group)
    if untriaged_only:
        stmt = stmt.where(TriageStay.acuity.is_(None))
    if high_risk_only:
        stmt = stmt.where(TriageStay.predicted_high_acuity.is_(True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(
        TriageStay.acuity.is_(None).asc(),  # untriaged sorts after triaged
        TriageStay.acuity.asc(),
        TriageStay.stay_id.asc(),
    ).limit(limit).offset(offset)

    rows = db.execute(stmt).scalars().all()
    return TriageStayPage(
        total=total, limit=limit, offset=offset,
        items=[TriageStayOut.model_validate(r) for r in rows],
    )


@router.get("/summary", response_model=TriageStaySummary)
def triage_stays_summary(db: Session = Depends(get_db)) -> TriageStaySummary:
    """
    Aggregate cohort counts for the dashboard's overview panel.

    Every count here is computed from the current table contents, never
    hard-coded — if the data is reloaded with different numbers, this
    endpoint reflects that on the next request.
    """
    total = db.scalar(select(func.count()).select_from(TriageStay)) or 0
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail="No triage stays loaded yet. Run `python load_triage_stays.py` from backend/.",
        )

    def _counts(column) -> dict[str, int]:
        rows = db.execute(select(column, func.count()).group_by(column)).all()
        return {("(none)" if k is None else str(k)): v for k, v in rows}

    acuity_counts = _counts(TriageStay.acuity)
    age_group_counts = _counts(TriageStay.age_group)
    arrival_counts = _counts(TriageStay.arrival_transport)
    disposition_counts = _counts(TriageStay.disposition)

    untriaged = db.scalar(
        select(func.count()).where(TriageStay.acuity.is_(None))
    ) or 0
    zero_vitals = db.scalar(
        select(func.count()).where(TriageStay.vitals_missing_count >= 6)
    ) or 0
    missing_history = db.scalar(
        select(func.count()).where(TriageStay.missing_history_flag.is_(True))
    ) or 0
    scored = db.scalar(
        select(func.count()).where(TriageStay.predicted_high_acuity.is_not(None))
    ) or 0
    predicted_high = db.scalar(
        select(func.count()).where(TriageStay.predicted_high_acuity.is_(True))
    ) or 0

    notes: list[str] = []
    if age_group_counts.get("Unknown", 0) == total:
        notes.append(
            "age_group is 'Unknown' for every stay: the source edstays.csv.gz in this "
            "demo extract has no anchor_age column, so pediatric/adult/geriatric "
            "thresholds cannot currently be applied. This is a data limitation, not a "
            "modeling choice — see ml/data_loader.py."
        )
    if untriaged:
        notes.append(
            f"{untriaged} stays have no recorded acuity (no matching MIMIC triage row). "
            "Preserved, not dropped; excluded from supervised training but still visible here."
        )
    if zero_vitals:
        notes.append(
            f"{zero_vitals} stays have 6 or more missing vitals fields. Do not read these "
            "as 'well' — a stay with nothing documented is not the same as a normal one."
        )
    if scored == 0:
        notes.append(
            "No stays have been scored yet. Run `python -m ml.train` then the batch "
            "scoring endpoint to populate predicted_high_acuity."
        )

    return TriageStaySummary(
        total_stays=total,
        untriaged_count=untriaged,
        acuity_counts=acuity_counts,
        age_group_counts=age_group_counts,
        arrival_transport_counts=arrival_counts,
        disposition_counts=disposition_counts,
        zero_vitals_count=zero_vitals,
        missing_history_count=missing_history,
        scored_count=scored,
        predicted_high_acuity_count=predicted_high,
        data_quality_notes=notes,
    )


@router.get("/{stay_id}", response_model=TriageStayOut)
def get_triage_stay(stay_id: int, db: Session = Depends(get_db)) -> TriageStayOut:
    """Fetch a single ED stay by its MIMIC-IV-ED `stay_id`."""
    stay = db.get(TriageStay, stay_id)
    if stay is None:
        raise HTTPException(status_code=404, detail=f"No triage stay with stay_id={stay_id}")
    return TriageStayOut.model_validate(stay)
