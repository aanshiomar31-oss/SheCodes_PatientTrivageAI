"""
ml/rule_engine.py
====================

PatientTriage.ai — Rule-Based Safety Engine
-------------------------------------------------
Deterministic, clinician-reviewable red-flag detection. This module has
no learned parameters and makes no probabilistic judgement — it is a
fixed set of named clinical criteria, each independently auditable.

Governing rule: "The AI recommends. The nurse decides." This module
does not decide either — it sets a FLOOR. The prediction pipeline
(`ml/predict.py`) always calls `evaluate(...)` before the ML ensemble,
and the ensemble's output is clamped so it can never assign a LESS
urgent priority than a fired rule requires. A rule can only escalate;
nothing downstream can undo that escalation. This is the same
architectural guarantee used throughout this project's rule/physiology
layers — a probabilistic estimate can raise concern, it cannot dismiss
a named clinical red flag.

Age-specific thresholds are mandatory per this project's design
principles: every vital-sign check here is evaluated against the
patient's own age-banded normal range, never a single adult-only scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Age-banded vital sign reference ranges.
#
# A fever of 38.5C is unremarkable in a toddler and a red flag in a frail
# 80-year-old; a heart rate of 110 is normal in an infant and alarming in
# an adult. Applying one adult-calibrated range to every patient is a
# silent safety risk this project's design principles explicitly forbid.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AgeBand:
    key: str
    label: str
    hr: tuple[float, float]
    rr: tuple[float, float]
    sbp: tuple[float, float]
    spo2_floor: float
    fever_c: float
    hypothermia_c: float


AGE_BANDS: list[AgeBand] = [
    AgeBand("infant", "Infant <1y", (100, 160), (30, 60), (60, 100), 95.0, 38.0, 36.0),
    AgeBand("child", "Child 1-11y", (70, 130), (18, 34), (75, 115), 95.0, 38.5, 36.0),
    AgeBand("adolescent", "Adolescent 12-17y", (60, 105), (12, 22), (90, 120), 95.0, 38.3, 35.5),
    AgeBand("adult", "Adult 18-64y", (60, 100), (12, 20), (100, 140), 95.0, 38.3, 35.5),
    AgeBand("geriatric", "Geriatric 65+", (60, 100), (12, 22), (110, 150), 95.0, 37.8, 36.2),
]


def band_for_age(age: float | None) -> AgeBand:
    """Missing age is treated as the widest, most conservative band (adult), never guessed younger or older."""
    if age is None:
        return AGE_BANDS[3]
    if age < 1:
        return AGE_BANDS[0]
    if age < 12:
        return AGE_BANDS[1]
    if age < 18:
        return AGE_BANDS[2]
    if age < 65:
        return AGE_BANDS[3]
    return AGE_BANDS[4]


# --------------------------------------------------------------------------- #
# Priority scale. Lower number = more urgent (matches MIMIC-IV-ED acuity).
# --------------------------------------------------------------------------- #
PRIORITY_LABELS = {1: "P1", 2: "P2", 3: "P3", 4: "P4", 5: "P5"}


@dataclass
class RuleHit:
    id: str
    priority_ceiling: int  # most urgent priority this rule requires (1 = most urgent)
    reason: str


@dataclass
class RuleEngineResult:
    escalated: bool
    priority_floor: int  # 1-5; the most urgent level any fired rule demands
    hits: list[RuleHit] = field(default_factory=list)
    age_band: str = "adult"

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS[self.priority_floor]

    def to_dict(self) -> dict:
        return {
            "escalated": self.escalated,
            "priority_floor": self.priority_floor,
            "priority_floor_label": self.priority_label,
            "age_band": self.age_band,
            "hits": [{"id": h.id, "priority_ceiling": h.priority_ceiling, "reason": h.reason} for h in self.hits],
        }


def _get(patient: dict, *keys, default=None):
    for k in keys:
        v = patient.get(k)
        if v is not None:
            return v
    return default


# --------------------------------------------------------------------------- #
# Red-flag rules. Each is a named, independently reviewable clinical
# criterion — data, in spirit, even though expressed as small functions —
# so a clinical governance reviewer can read exactly what fires and why.
# --------------------------------------------------------------------------- #
def _rule_critical_hypoxia(p: dict, band: AgeBand) -> RuleHit | None:
    spo2 = _get(p, "o2sat", "o2_sat", "spo2")
    if spo2 is not None and spo2 < 90:
        return RuleHit("CRITICAL_HYPOXIA", 1, f"SpO2 {spo2:.0f}% — critically low oxygen saturation")
    return None


def _rule_severe_respiratory_distress(p: dict, band: AgeBand) -> RuleHit | None:
    rr = _get(p, "resprate", "resp_rate")
    spo2 = _get(p, "o2sat", "o2_sat", "spo2")
    if rr is not None and (rr > band.rr[1] * 1.5 or rr < band.rr[0] * 0.5):
        return RuleHit("SEVERE_RESP_DISTRESS", 1, f"RR {rr:.0f} — severe respiratory distress for {band.label}")
    if spo2 is not None and spo2 < 93 and rr is not None and rr > band.rr[1]:
        return RuleHit("SEVERE_RESP_DISTRESS", 1, "Low SpO2 with tachypnoea — severe respiratory distress")
    return None


def _rule_chest_pain_diaphoresis(p: dict, band: AgeBand) -> RuleHit | None:
    complaint = str(_get(p, "chief_complaint", "chiefcomplaint", default="")).lower()
    diaphoretic = bool(p.get("diaphoresis")) or "diaphores" in complaint or "sweating" in complaint
    chest_pain = "chest pain" in complaint or "chest discomfort" in complaint or bool(p.get("chest_pain"))
    age = p.get("age")
    if chest_pain and diaphoretic and (age is None or age > 30):
        return RuleHit("CHEST_PAIN_DIAPHORESIS", 1, "Chest pain with diaphoresis — possible acute coronary syndrome")
    return None


def _rule_stroke_symptoms(p: dict, band: AgeBand) -> RuleHit | None:
    complaint = str(_get(p, "chief_complaint", "chiefcomplaint", default="")).lower()
    keywords = ("stroke", "facial droop", "slurred speech", "one-sided weakness", "one sided weakness", "fast positive")
    if bool(p.get("fast_positive")) or any(k in complaint for k in keywords):
        return RuleHit("STROKE_SYMPTOMS", 1, "Stroke symptoms (FAST-positive) — thrombolysis window is time-critical")
    return None


def _rule_unresponsive(p: dict, band: AgeBand) -> RuleHit | None:
    mental = str(_get(p, "mental_status", default="")).lower()
    if mental in ("unresponsive", "pain", "unresponsive to pain") or bool(p.get("unresponsive")):
        return RuleHit("UNRESPONSIVE", 1, "Patient unresponsive or responds only to pain")
    return None


def _rule_shock(p: dict, band: AgeBand) -> RuleHit | None:
    sbp = _get(p, "sbp")
    hr = _get(p, "heartrate", "heart_rate")
    if sbp is not None and hr is not None and sbp < band.sbp[0] * 0.85 and hr > 110:
        return RuleHit("SHOCK", 1, f"SBP {sbp:.0f} with HR {hr:.0f} — hypotension with tachycardia, possible shock")
    return None


def _rule_seizure_or_airway(p: dict, band: AgeBand) -> RuleHit | None:
    if bool(p.get("seizing")) or bool(p.get("airway_compromise")) or bool(p.get("stridor")):
        return RuleHit("AIRWAY_OR_SEIZURE", 1, "Active seizure or airway compromise")
    return None


def _rule_neonate_fever(p: dict, band: AgeBand) -> RuleHit | None:
    age = p.get("age")
    temp_c = _to_celsius(_get(p, "temperature"))
    if age is not None and age < (28 / 365) and temp_c is not None and temp_c >= 38.0:
        return RuleHit("NEONATE_FEVER", 1, "Fever in an infant under 28 days")
    return None


def _rule_moderate_derangement(p: dict, band: AgeBand) -> RuleHit | None:
    """Below red-flag severity but still clinically urgent — P2 ceiling, not P1."""
    sbp = _get(p, "sbp")
    hr = _get(p, "heartrate", "heart_rate")
    rr = _get(p, "resprate", "resp_rate")
    spo2 = _get(p, "o2sat", "o2_sat", "spo2")
    hits = 0
    if hr is not None and (hr > band.hr[1] or hr < band.hr[0]):
        hits += 1
    if rr is not None and (rr > band.rr[1] or rr < band.rr[0]):
        hits += 1
    if sbp is not None and (sbp > band.sbp[1] or sbp < band.sbp[0]):
        hits += 1
    if spo2 is not None and spo2 < band.spo2_floor:
        hits += 1
    if hits >= 2:
        return RuleHit("MODERATE_DERANGEMENT", 2, f"{hits} vitals outside the normal range for {band.label}")
    return None


def _to_celsius(temp: float | None) -> float | None:
    """MIMIC-IV-ED records temperature in Fahrenheit; this project's readable
    frame preserves source units, so convert defensively rather than assume."""
    if temp is None:
        return None
    return (temp - 32) * 5 / 9 if temp > 50 else temp


RULES: list[Callable[[dict, AgeBand], RuleHit | None]] = [
    _rule_critical_hypoxia,
    _rule_severe_respiratory_distress,
    _rule_chest_pain_diaphoresis,
    _rule_stroke_symptoms,
    _rule_unresponsive,
    _rule_shock,
    _rule_seizure_or_airway,
    _rule_neonate_fever,
    _rule_moderate_derangement,
]


def evaluate(patient: dict) -> RuleEngineResult:
    """
    Run every red-flag rule against a patient dict and return the
    resulting priority floor.

    Parameters
    ----------
    patient : dict
        Patient data using the field names accepted by `ml.predict.predict`
        (see that module's docstring). Missing fields are treated as
        "unknown", never as "normal" — a rule simply cannot fire on data
        it does not have, which is reflected in `uncertainty.py`'s
        missing-data penalty, not silently absorbed here.

    Returns
    -------
    RuleEngineResult
        `priority_floor` is the most urgent priority any fired rule
        demands (5 = no rule fired). `escalated` is True whenever any
        rule fired at all, regardless of its ceiling.
    """
    band = band_for_age(patient.get("age"))
    hits: list[RuleHit] = []

    for rule in RULES:
        try:
            hit = rule(patient, band)
        except Exception as exc:  # noqa: BLE001 — a malformed field must never crash triage
            logger.warning("Rule %s raised %s — skipped, not treated as a pass.", rule.__name__, exc)
            continue
        if hit is not None:
            hits.append(hit)

    floor = min((h.priority_ceiling for h in hits), default=5)
    result = RuleEngineResult(escalated=bool(hits), priority_floor=floor, hits=hits, age_band=band.key)

    if result.escalated:
        logger.info(
            "Rule engine escalation: floor=%s hits=%s",
            result.priority_label, [h.id for h in hits],
        )
    return result
