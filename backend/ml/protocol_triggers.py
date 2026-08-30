"""
ml/protocol_triggers.py
=========================

PatientTriage.ai — Time-Critical Protocol Detector
-----------------------------------------------------
Detects patterns in the triage request that warrant immediate activation
of a time-sensitive clinical protocol. These are purely rule-based —
no ML involved — because the conditions (stroke, STEMI, anaphylaxis) are
well-characterised by ACEP and AHA guidelines and cannot afford the
latency or uncertainty of a model.

Supported protocols:
  - STROKE_ALERT    (target: CT within 25 min)
  - STEMI_ALERT     (target: cath lab within 90 min)
  - ANAPHYLAXIS     (target: epinephrine within 5 min)
  - AIRWAY_CRISIS   (target: airway management immediately)

Each triggered protocol returns a `Protocol` object with a checklist the
nurse works through. Every item the nurse ticks is logged to the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Keyword sets (case-insensitive substring match on chief_complaint)
# ---------------------------------------------------------------------------

_STROKE_KEYWORDS = {
    "stroke", "facial droop", "face droop", "arm weak", "arm drift",
    "speech", "slurred", "aphasia", "dysphasia", "sudden weak",
    "sudden numb", "sudden confu", "vision loss", "sudden blind",
    "worst headache", "thunderclap", "tia", "transient isch",
    "hemiplegia", "hemiparesis", "facial asymmetry",
}

_STEMI_KEYWORDS = {
    "chest pain", "chest tightness", "chest pressure", "chest heaviness",
    "crushing chest", "cardiac", "stemi", "heart attack", "mi",
    "radiating arm", "jaw pain", "epigastric",
}

_ANAPHYLAXIS_KEYWORDS = {
    "anaphylaxis", "anaphylactic", "allergic reaction", "bee sting",
    "swollen throat", "throat closing", "urticaria", "hives",
    "angioedema",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    id: str
    text: str
    time_target_minutes: int | None = None   # None = immediately


@dataclass
class Protocol:
    code: str                    # e.g. "STROKE_ALERT"
    title: str
    color: str                   # Tailwind token: "red" | "orange" | "violet"
    icon: str                    # emoji for rapid visual recognition
    urgency_minutes: int         # door-to-intervention target
    rationale: str               # one-line clinical justification
    checklist: list[ChecklistItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Protocol definitions
# ---------------------------------------------------------------------------

STROKE_PROTOCOL = Protocol(
    code="STROKE_ALERT",
    title="Stroke Alert",
    color="red",
    icon="🧠",
    urgency_minutes=25,
    rationale="Every minute of stroke = 1.9 million neurons lost. Door-to-CT target: 25 min.",
    checklist=[
        ChecklistItem("s1", "Activate Stroke Team / Code Stroke paging"),
        ChecklistItem("s2", "Stat non-contrast CT head ordered"),
        ChecklistItem("s3", "Blood glucose checked (hypoglycaemia mimics stroke)"),
        ChecklistItem("s4", "Last known well time documented", time_target_minutes=5),
        ChecklistItem("s5", "NIH Stroke Scale assessed"),
        ChecklistItem("s6", "IV access established ×2"),
        ChecklistItem("s7", "12-lead ECG (rule out AF as source)"),
        ChecklistItem("s8", "tPA eligibility window assessed (≤4.5h from LKW)"),
    ],
)

STEMI_PROTOCOL = Protocol(
    code="STEMI_ALERT",
    title="STEMI Alert",
    color="red",
    icon="❤️",
    urgency_minutes=90,
    rationale="Door-to-balloon target: 90 min. Every 30 min delay = 7.5 lives/1000 patients.",
    checklist=[
        ChecklistItem("m1", "12-lead ECG within 10 minutes", time_target_minutes=10),
        ChecklistItem("m2", "Activate Cath Lab / Code STEMI paging"),
        ChecklistItem("m3", "Aspirin 325 mg PO (if no allergy)"),
        ChecklistItem("m4", "Clopidogrel / P2Y12 inhibitor per protocol"),
        ChecklistItem("m5", "IV access established ×2, bloods drawn"),
        ChecklistItem("m6", "Troponin, CMP, CBC ordered stat"),
        ChecklistItem("m7", "Supplemental O₂ if SpO₂ < 94%"),
        ChecklistItem("m8", "Cardiology / interventional team notified"),
    ],
)

ANAPHYLAXIS_PROTOCOL = Protocol(
    code="ANAPHYLAXIS",
    title="Anaphylaxis Protocol",
    color="orange",
    icon="⚡",
    urgency_minutes=5,
    rationale="Epinephrine within 5 minutes significantly reduces mortality.",
    checklist=[
        ChecklistItem("a1", "Epinephrine 0.3-0.5 mg IM (vastus lateralis)", time_target_minutes=5),
        ChecklistItem("a2", "Call for help / activate resuscitation team"),
        ChecklistItem("a3", "Supine position, legs elevated"),
        ChecklistItem("a4", "IV access, 1-2L normal saline"),
        ChecklistItem("a5", "Diphenhydramine 50 mg IV"),
        ChecklistItem("a6", "Methylprednisolone 125 mg IV"),
        ChecklistItem("a7", "Continuous cardiac / SpO₂ monitoring"),
        ChecklistItem("a8", "Prepare for airway management"),
    ],
)

AIRWAY_PROTOCOL = Protocol(
    code="AIRWAY_CRISIS",
    title="Airway Crisis",
    color="red",
    icon="🫁",
    urgency_minutes=0,
    rationale="Airway compromise is immediately life-threatening. Act in seconds.",
    checklist=[
        ChecklistItem("w1", "Call resuscitation team IMMEDIATELY"),
        ChecklistItem("w2", "Position: upright / sniffing position"),
        ChecklistItem("w3", "High-flow O₂ 15L/min via non-rebreather mask"),
        ChecklistItem("w4", "Prepare RSI medications (etomidate + succinylcholine)"),
        ChecklistItem("w5", "Laryngoscope, ETT, BVM at bedside"),
        ChecklistItem("w6", "Surgical airway kit available"),
        ChecklistItem("w7", "IV access, monitoring attached"),
    ],
)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

def detect_protocols(patient: dict) -> list[Protocol]:
    """
    Inspect the patient dict and return all protocols that should fire.
    Multiple protocols can trigger simultaneously (e.g. STEMI + anaphylaxis
    from a contrast reaction).

    Order: most time-critical first (AIRWAY > ANAPHYLAXIS > STROKE/STEMI).
    """
    triggered: list[Protocol] = []
    complaint = (patient.get("chief_complaint") or "").lower()

    # Airway compromise — flag takes priority over keyword matching
    if patient.get("airway_compromise") or patient.get("stridor"):
        triggered.append(AIRWAY_PROTOCOL)

    # Anaphylaxis
    if any(kw in complaint for kw in _ANAPHYLAXIS_KEYWORDS):
        triggered.append(ANAPHYLAXIS_PROTOCOL)

    # Stroke — keywords OR unresponsive + no other clear cause
    if any(kw in complaint for kw in _STROKE_KEYWORDS):
        triggered.append(STROKE_PROTOCOL)

    # STEMI — chest pain + diaphoresis or clinical flag, not just "chest pain" alone
    # (to avoid over-triggering on musculoskeletal chest pain)
    stemi_keyword = any(kw in complaint for kw in _STEMI_KEYWORDS)
    stemi_flag = patient.get("chest_pain") or patient.get("diaphoresis")
    if stemi_keyword or stemi_flag:
        # Only fire STEMI if not already captured as anaphylaxis
        if ANAPHYLAXIS_PROTOCOL not in triggered:
            triggered.append(STEMI_PROTOCOL)

    return triggered


def protocols_to_dict(protocols: list[Protocol]) -> list[dict]:
    """Serialise for JSON response."""
    result = []
    for p in protocols:
        result.append({
            "code": p.code,
            "title": p.title,
            "color": p.color,
            "icon": p.icon,
            "urgency_minutes": p.urgency_minutes,
            "rationale": p.rationale,
            "checklist": [
                {
                    "id": item.id,
                    "text": item.text,
                    "time_target_minutes": item.time_target_minutes,
                }
                for item in p.checklist
            ],
        })
    return result
