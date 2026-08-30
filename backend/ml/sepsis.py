"""
ml/sepsis.py
==============

PatientTriage.ai — Sepsis Early Warning Scorer
--------------------------------------------------
Computes qSOFA (Quick Sequential Organ Failure Assessment) and SIRS
criteria from patient vitals. These are never used to *set* a priority
automatically — they are advisory flags that surface to the nurse
alongside the AI recommendation, consistent with the platform's
"The AI recommends. The nurse decides." governing rule.

Clinical references:
  - qSOFA: Seymour et al., JAMA 2016 (doi:10.1001/jama.2016.0894)
  - SIRS:  Bone et al., Chest 1992
  - Surviving Sepsis Campaign: https://www.survivingsepsis.org
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Safe-interval thresholds by priority
# ---------------------------------------------------------------------------
SAFE_WAIT_MINUTES: dict[str, int] = {
    "P1": 0,
    "P2": 15,
    "P3": 30,
    "P4": 60,
    "P5": 120,
}


# ---------------------------------------------------------------------------
# qSOFA
# ---------------------------------------------------------------------------

def _qsofa_score(patient: dict) -> tuple[int, list[str]]:
    """
    Compute qSOFA (0-3). Each criterion scores 1 point:
      1. Altered mentation         — approximated by unresponsive flag
      2. Respiratory rate ≥ 22/min
      3. Systolic BP ≤ 100 mmHg

    Returns (score, list_of_triggered_criteria).
    """
    score = 0
    criteria: list[str] = []

    if patient.get("unresponsive"):
        score += 1
        criteria.append("Altered mentation (unresponsive at triage)")

    rr = patient.get("resprate")
    if rr is not None and rr >= 22:
        score += 1
        criteria.append(f"RR {rr:.0f} ≥ 22/min")

    sbp = patient.get("sbp")
    if sbp is not None and sbp <= 100:
        score += 1
        criteria.append(f"SBP {sbp:.0f} ≤ 100 mmHg")

    return score, criteria


# ---------------------------------------------------------------------------
# SIRS
# ---------------------------------------------------------------------------

def _sirs_count(patient: dict) -> tuple[int, list[str]]:
    """
    Count SIRS criteria met (0-4). ≥ 2 = SIRS positive.
      1. Temp > 38 °C or < 36 °C
      2. Heart rate > 90 bpm
      3. Respiratory rate > 20/min
      4. WBC not available at intake — omitted
    """
    count = 0
    criteria: list[str] = []

    temp = patient.get("temperature")
    if temp is not None:
        # Fahrenheit conversion if value looks like °F (>50 is the heuristic used elsewhere)
        if temp > 50:
            temp_c = (temp - 32) * 5 / 9
        else:
            temp_c = temp
        if temp_c > 38.0 or temp_c < 36.0:
            count += 1
            criteria.append(f"Temp {temp_c:.1f} °C (outside 36-38 °C)")

    hr = patient.get("heartrate")
    if hr is not None and hr > 90:
        count += 1
        criteria.append(f"HR {hr:.0f} > 90 bpm")

    rr = patient.get("resprate")
    if rr is not None and rr > 20:
        count += 1
        criteria.append(f"RR {rr:.0f} > 20/min")

    return count, criteria


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class SepsisResult:
    qsofa_score: int
    qsofa_criteria: list[str]
    sirs_count: int
    sirs_criteria: list[str]
    alert: bool           # True if qSOFA ≥ 2
    risk_level: str       # "high" | "moderate" | "low"
    message: str
    requires_acknowledgement: bool  # nurse must confirm before de-escalating

    # Time-to-antibiotic tracking — populated if alert fires
    antibiotic_target_minutes: int = field(default=60)


def assess_sepsis(patient: dict) -> SepsisResult:
    """
    Run qSOFA + SIRS and return a SepsisResult.
    Called from the triage route immediately after predict().
    """
    qsofa, qsofa_criteria = _qsofa_score(patient)
    sirs, sirs_criteria = _sirs_count(patient)

    # qSOFA ≥ 2 = high risk; qSOFA 1 + SIRS ≥ 2 = moderate
    if qsofa >= 2:
        alert = True
        risk_level = "high"
        message = (
            f"⚠️ Sepsis HIGH RISK — qSOFA {qsofa}/3. "
            "Activate sepsis bundle: blood cultures ×2, lactate, broad-spectrum antibiotics within 1 hour."
        )
        requires_acknowledgement = True
    elif qsofa == 1 and sirs >= 2:
        alert = True
        risk_level = "moderate"
        message = (
            f"⚠️ Possible sepsis — qSOFA {qsofa}/3, SIRS {sirs}/4. "
            "Monitor closely. Consider blood cultures and early IV access."
        )
        requires_acknowledgement = True
    else:
        alert = False
        risk_level = "low"
        message = f"Sepsis screen negative (qSOFA {qsofa}/3, SIRS {sirs}/4)."
        requires_acknowledgement = False

    return SepsisResult(
        qsofa_score=qsofa,
        qsofa_criteria=qsofa_criteria,
        sirs_count=sirs,
        sirs_criteria=sirs_criteria,
        alert=alert,
        risk_level=risk_level,
        message=message,
        requires_acknowledgement=requires_acknowledgement,
    )
