"""
schemas/triage.py
====================

PatientTriage.ai — Triage Recommendation Schemas
--------------------------------------------------------
Request/response models for `POST /api/v1/triage`. The response model
matches the Hybrid Intelligence Layer's output contract exactly (see
`ml/predict.py::predict`), so the API layer adds validation and
persistence but never reshapes the recommendation itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TriageRequest(BaseModel):
    """
    Patient data submitted for triage. Every clinical field is optional
    — per this platform's design principle, missing data increases
    uncertainty rather than blocking a recommendation. `age` and at
    least one vital sign are required so the rule engine and ensemble
    have something to reason about; a request with neither is rejected
    rather than silently scored as a well adult.
    """

    age: float | None = Field(None, ge=0, le=120)
    gender: str | None = Field(None, max_length=1)
    heartrate: float | None = Field(None, ge=0, le=300)
    sbp: float | None = Field(None, ge=0, le=300)
    dbp: float | None = Field(None, ge=0, le=200)
    resprate: float | None = Field(None, ge=0, le=100)
    temperature: float | None = Field(
        None, ge=30, le=115,
        description="Celsius or Fahrenheit — detected automatically (values <=50 are treated as Celsius, "
                    "matching ml.model_utils._to_celsius). Do not pre-convert.",
    )
    o2sat: float | None = Field(None, ge=0, le=100)
    pain: float | None = Field(None, ge=0, le=10)
    chief_complaint: str | None = None

    arrival_transport: str | None = None
    arrival_hour: int | None = Field(None, ge=0, le=23)
    night_shift_flag: bool | None = None
    weekend_flag: bool | None = None

    medications: list[str] | None = None
    history: dict | None = None
    zero_history: bool | None = None
    returning_patient: bool | None = Field(
        None, description="True if this patient has a prior record on file. Distinct from `history`, "
                          "which carries structured comorbidity/admission data when known.",
    )
    previous_history: str | None = Field(
        None, max_length=2000, description="Free-text prior history noted at intake, if any.",
    )

    # Rule-engine finding flags — explicit clinical observations a nurse
    # can check at intake that a vitals-only model cannot infer.
    chest_pain: bool = False
    diaphoresis: bool = False
    fast_positive: bool = False
    unresponsive: bool = False
    seizing: bool = False
    airway_compromise: bool = False
    stridor: bool = False

    @model_validator(mode="after")
    def _require_some_signal(self) -> "TriageRequest":
        vitals = (self.heartrate, self.sbp, self.dbp, self.resprate, self.temperature, self.o2sat)
        if self.age is None and all(v is None for v in vitals) and not self.chief_complaint:
            raise ValueError(
                "At least age, one vital sign, or a chief complaint is required — "
                "an empty request cannot be safely triaged."
            )
        return self

    def to_patient_dict(self) -> dict:
        """Convert to the plain dict `ml.predict.predict()` expects."""
        return self.model_dump(exclude_none=False)


class TriageResponse(BaseModel):
    """
    Hybrid Intelligence Layer output, extended with the two fields the
    live workflow needs beyond a bare recommendation: `patient_id` (so
    the nurse can find this patient again in the Live Queue) and
    `clinical_priority_score` (see app/services/cps.py — an initial
    value computed at intake with wait_score=0, since the patient has
    just arrived; it updates as they wait once visible in the queue).
    """

    patient_id: str = Field(..., examples=["ED0204"])
    priority: str = Field(..., examples=["P2"])
    risk_score: int = Field(..., ge=0, le=100)
    clinical_priority_score: int = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty_reason: str | None = None
    top_features: list[str]
    escalated: bool
    governing_rule: str = "The AI recommends. The nurse decides."
    prediction_id: str | None = Field(
        None, description="Audit log id this recommendation was recorded under, if persistence succeeded."
    )

    # ---------------------------------------------------------------- Sepsis
    sepsis_alert: bool = False
    sepsis_risk_level: str = "low"          # "high" | "moderate" | "low"
    sepsis_qsofa: int = 0
    sepsis_criteria: list[str] = Field(default_factory=list)
    sepsis_message: str = ""
    sepsis_requires_acknowledgement: bool = False

    # --------------------------------------------------------- Protocol triggers
    triggered_protocols: list[dict] = Field(
        default_factory=list,
        description="List of time-critical protocols (Stroke/STEMI/Anaphylaxis/Airway) that fired.",
    )
