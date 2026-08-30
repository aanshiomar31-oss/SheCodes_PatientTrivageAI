"""
app/services/cps.py
======================

PatientTriage.ai — Clinical Priority Score
------------------------------------------------
    CPS = 0.45 * ml_risk + 0.25 * rule_score + 0.15 * wait_score
          + 0.10 * age_vulnerability - 0.05 * uncertainty

All five components are in [0, 1]. CPS answers "which P2 patient needs
attention first", not "what is this patient's priority" — that's what
`priority` already is. CPS is a ranking AID surfaced to the nurse, never
a value that moves a patient in the queue by itself; see
`app/api/routes/queue.py`'s docstring for how that principle is
enforced at the API layer.

Extracted here (rather than duplicated in triage.py, queue.py, and
vitals.py, all three of which need to compute CPS at different moments
in the workflow) so the formula has exactly one implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.triage_stay import TriageStay

PRIORITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}
SAFE_INTERVAL_MINUTES = {"P1": 0, "P2": 10, "P3": 30, "P4": 60, "P5": 120}


def age_vulnerability(age: float | None) -> float:
    """0-1: higher for the very young and the elderly, lowest for healthy adults."""
    if age is None:
        return 0.4  # unknown age is treated as moderately vulnerable, never zero
    if age < 1:
        return 1.0
    if age < 12:
        return 0.7
    if age < 65:
        return 0.3
    if age < 80:
        return 0.7
    return 0.9


def wait_score(waited_minutes: float, priority_label: str) -> float:
    """0-1: how far past this priority's safe reassessment interval the wait already is."""
    safe_minutes = SAFE_INTERVAL_MINUTES.get(priority_label, 60)
    if safe_minutes == 0:
        return 1.0 if waited_minutes > 0 else 0.5
    return min(1.0, waited_minutes / (safe_minutes * 2))


def minutes_waited(stay: TriageStay) -> float:
    if stay.loaded_at is None:
        return 0.0
    arrived = stay.loaded_at if stay.loaded_at.tzinfo else stay.loaded_at.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - arrived).total_seconds() / 60.0)


def compute_cps(stay: TriageStay, recommendation: dict, age: float | None = None) -> dict:
    """
    Returns the CPS and its five components, each already in [0, 1], so
    the frontend can render the formula breakdown directly rather than
    reverse-engineering it from a single number.

    `age` is accepted separately from `stay` because `TriageStay` has no
    age column (this MIMIC-IV-ED demo extract has no source age data —
    see `app/models/triage_stay.py`); a freshly-submitted intake request
    DOES carry age, so callers scoring a live submission can pass it
    through even though it can't be persisted onto the stay record.
    """
    ml_risk = recommendation.get("risk_score", 0) / 100.0
    priority_label = recommendation.get("priority", "P3")
    rule_score = (
        1.0 if recommendation.get("escalated")
        else max(0.0, 1.0 - (PRIORITY_RANK.get(priority_label, 3) - 1) / 4)
    )
    waited = minutes_waited(stay)
    wait = wait_score(waited, priority_label)
    age_vuln = age_vulnerability(age)
    uncertainty = 1.0 - recommendation.get("confidence", 0.5)

    cps = 0.45 * ml_risk + 0.25 * rule_score + 0.15 * wait + 0.10 * age_vuln - 0.05 * uncertainty
    cps = round(max(0.0, min(1.0, cps)), 4)

    return {
        "cps": cps,
        "cps_100": round(cps * 100),
        "components": {
            "ml_risk": round(ml_risk, 4),
            "rule_score": round(rule_score, 4),
            "wait_score": round(wait, 4),
            "age_vulnerability": round(age_vuln, 4),
            "uncertainty": round(uncertainty, 4),
        },
        "waited_minutes": round(waited, 1),
    }


def format_patient_id(stay_id: int) -> str:
    """'ED' + a stable 4-digit tag derived from stay_id (1-9999, never 0000
    — an all-zero ID reads as a null/placeholder rather than a real patient)."""
    return f"ED{(stay_id % 9999) + 1:04d}"
