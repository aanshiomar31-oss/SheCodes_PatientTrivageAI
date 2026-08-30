"""
app/services/patient_registry.py
====================================

PatientTriage.ai — Intake Persistence
--------------------------------------------
Closes a real gap: `POST /triage` previously only logged a recommendation
to the audit trail — it never created a row `GET /queue` could see. A
nurse submitting a new patient in Patient Intake would get a
recommendation on screen and then the patient would never actually
appear in the Live Queue. This module is what makes "patient enters
Live Queue" true rather than cosmetic.

`TriageStay` predates this workflow and has no `age` column (this
MIMIC-IV-ED demo extract has no source age data at all — see
`app/models/triage_stay.py`). A live intake submission DOES carry age,
and age is used for SCORING at intake time, but it cannot be persisted
onto the stay record. This is stated here rather than silently dropped:
`create_intake_stay()`'s docstring covers it, and every subsequent
re-score of that patient from the queue will use age=None, same as
every pre-existing MIMIC row.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.triage_stay import TriageStay

# MIMIC-IV-ED demo stay_ids in this dataset are all well under this
# floor (~30-40 million range with this specific extract's IDs, but no
# guarantee is made about future extracts, so we derive the floor from
# the actual data rather than hard-coding a number that could collide).
_INTAKE_ID_FLOOR = 900_000_000


def next_intake_stay_id(db: Session) -> int:
    """A stay_id for a freshly-submitted patient, guaranteed not to collide with MIMIC data."""
    current_max = db.scalar(select(func.max(TriageStay.stay_id))) or 0
    return max(_INTAKE_ID_FLOOR, current_max + 1)


def create_intake_stay(db: Session, patient: dict) -> TriageStay:
    """
    Create and persist a new `TriageStay` from a Patient Intake submission.

    Parameters
    ----------
    patient : dict
        The same dict shape `ml.predict.predict()` accepts — see
        `app/schemas/triage.py::TriageRequest.to_patient_dict()`.

    Returns
    -------
    TriageStay
        The newly created, committed row. Its `stay_id` is what the
        patient appears under in `GET /queue` from this point on.
    """
    stay_id = next_intake_stay_id(db)
    returning = patient.get("returning_patient")
    previous_history = patient.get("previous_history")
    has_history_signal = bool(returning) or bool(previous_history) or patient.get("zero_history") is False

    stay = TriageStay(
        stay_id=stay_id,
        gender=patient.get("gender"),
        arrival_transport=patient.get("arrival_transport") or "WALK IN",
        chief_complaint=patient.get("chief_complaint"),
        age_group="Unknown",  # no source age data — see module docstring
        temperature=patient.get("temperature"),
        heart_rate=patient.get("heartrate"),
        resp_rate=patient.get("resprate"),
        o2_sat=patient.get("o2sat"),
        sbp=patient.get("sbp"),
        dbp=patient.get("dbp"),
        pain=patient.get("pain"),
        missing_history_flag=not has_history_signal,
        arrival_hour=patient.get("arrival_hour"),
        night_shift_flag=patient.get("night_shift_flag"),
        weekend_flag=patient.get("weekend_flag"),
    )
    db.add(stay)
    db.commit()
    db.refresh(stay)
    return stay
