"""
models/triage_stay.py
========================

PatientTriage.ai — Triage Stay Model
---------------------------------------
Persists ED stays from the MIMIC-IV-ED (Demo) source data in a
CLINICALLY READABLE form — raw units (temperature in the source scale,
heart rate in bpm, chief complaint as text), not the scaled/one-hot
encoding used for model training.

Why this table does NOT mirror `data/processed_triage.csv` 1:1
-----------------------------------------------------------------
`processed_triage.csv` is the ML-ready artifact: numeric columns are
standard-scaled (a `temperature` of `-0.35` there is not a real
temperature) and categoricals are one-hot encoded (`race_WHITE`,
`disposition_HOME`, ...). That is the right shape for a model and the
wrong shape for a database table:

* it is not human-readable — a nurse-facing dashboard showing
  "temperature: -0.35" is actively misleading;
* it is schema-fragile — a new `race` value appearing in a future data
  refresh would require a new column and a migration, when it should
  just be a new row value;
* the scaling is fit-dependent — the same raw stay can map to a
  different scaled value depending on what else was in the training
  batch, which makes it a poor thing to persist as "the" record.

This table instead stores the merged + feature-engineered frame BEFORE
the sklearn `ColumnTransformer` step (see `ml.preprocess.run_preprocessing`,
steps 1-5) via `ml.load_readable_stays()`. The CSV remains the
ML training artifact, loaded directly by `ml/train.py` — the two are
kept deliberately separate rather than forced into one shape.

Clinical safety principles enforced here
-------------------------------------------
* `acuity` is nullable — 15 MIMIC demo stays have no matching triage
  record. NULL means "not triaged", never coerced to a default level.
* Every vital is nullable — NULL means "not recorded", distinct from a
  documented normal value.
* `predicted_*` columns are populated by a batch scoring step
  (`app.api.routes.model`), never by this model itself, and are always
  reviewable/overridable per the governing rule. They record what the
  model recommended; they are not the record of what happened to the
  patient.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TriageStay(Base):
    """
    One row per ED stay (`stay_id`), in clinically readable units.

    Columns
    -------
    stay_id : int
        MIMIC-IV-ED stay identifier. Primary key — unique per ED encounter.
    subject_id, hadm_id : int | None
        Patient and hospital-admission identifiers, where available.
    gender, race, arrival_transport, disposition : str | None
        Raw categorical values as documented, e.g. "WALK IN", "AMBULANCE".
    age_group : str
        "Pediatric" / "Adult" / "Geriatric" / "Unknown" (see
        `ml.features.add_age_group`). Currently "Unknown" for every row
        in this demo extract because `anchor_age` is absent from the
        source `edstays.csv.gz` — surfaced, not hidden, via the data
        quality report and the `/triage-stays/summary` endpoint.
    chief_complaint : str | None
        Free-text presenting complaint.
    temperature, heart_rate, resp_rate, o2_sat, sbp, dbp, pain : float | None
        Vitals in their original documented units. NULL = not recorded.
    shock_index, pulse_pressure, mean_arterial_pressure : float | None
        Engineered hemodynamic composites (see `ml.features`).
    abnormal_vitals_count : int
        Vitals outside the age-group-specific normal range (0 if none
        available to check).
    vitals_missing_count : int
        Vitals never documented at all — distinct from "checked and
        normal". A stay with every vital missing is not the same as a
        well patient; see `ml.features.add_vitals_missing_count`.
    missing_history_flag : bool
        True if chief complaint (or other tracked history field) is blank.
    arrival_hour : int | None
        Hour of day (0-23) the patient arrived.
    night_shift_flag, weekend_flag : bool | None
        NULL when the arrival timestamp could not be parsed.
    acuity : int | None
        Ground-truth MIMIC triage acuity (1-5). NULL for untriaged stays
        — preserved, never imputed.
    predicted_high_acuity : bool | None
        Model recommendation: True = the model flags this stay for
        urgent review (predicted acuity 1-2). NULL until scored.
    predicted_probability : float | None
        Calibrated probability backing `predicted_high_acuity`.
    model_version : str | None
        Identifies which trained artifact produced the prediction, so a
        stale prediction is always attributable to a specific model run.
    scored_at : datetime | None
        When the prediction was written.
    recommended_priority : str | None
        The priority string ("P1"–"P4") returned by the ML pipeline at
        intake time. NULL for pre-existing MIMIC rows. Written by
        `app/api/routes/triage.py` after every live intake so the
        waiting-room monitor can read it without re-running predict().
    recommended_confidence : float | None
        The confidence score (0–1) returned alongside `recommended_priority`.
    """

    __tablename__ = "triage_stays"

    stay_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    subject_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    hadm_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    race: Mapped[str | None] = mapped_column(String(64), nullable=True)
    arrival_transport: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    age_group: Mapped[str] = mapped_column(String(16), default="Unknown", index=True)

    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)

    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    resp_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    o2_sat: Mapped[float | None] = mapped_column(Float, nullable=True)
    sbp: Mapped[float | None] = mapped_column(Float, nullable=True)
    dbp: Mapped[float | None] = mapped_column(Float, nullable=True)
    pain: Mapped[float | None] = mapped_column(Float, nullable=True)

    shock_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    pulse_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_arterial_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)

    abnormal_vitals_count: Mapped[int] = mapped_column(Integer, default=0)
    vitals_missing_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_history_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    arrival_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    night_shift_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    weekend_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    acuity: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    predicted_high_acuity: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    predicted_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Live-intake recommendation — written by triage.py, read by monitor.py
    recommended_priority: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    recommended_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<TriageStay stay_id={self.stay_id} acuity={self.acuity} age_group={self.age_group!r}>"
