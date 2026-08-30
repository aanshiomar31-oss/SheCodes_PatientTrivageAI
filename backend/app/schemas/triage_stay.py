"""
schemas/triage_stay.py
=========================

PatientTriage.ai — Triage Stay Schemas
------------------------------------------
Response models for `GET /api/v1/triage-stays*`. Mirrors
`app.models.triage_stay.TriageStay` field-for-field so the API contract
and the database schema cannot silently drift apart.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TriageStayOut(BaseModel):
    """One ED stay, in clinically readable units."""

    model_config = ConfigDict(from_attributes=True)

    stay_id: int
    subject_id: int | None
    hadm_id: int | None

    gender: str | None
    race: str | None
    arrival_transport: str | None
    disposition: str | None
    age_group: str

    chief_complaint: str | None

    temperature: float | None
    heart_rate: float | None
    resp_rate: float | None
    o2_sat: float | None
    sbp: float | None
    dbp: float | None
    pain: float | None

    shock_index: float | None
    pulse_pressure: float | None
    mean_arterial_pressure: float | None

    abnormal_vitals_count: int
    vitals_missing_count: int
    missing_history_flag: bool

    arrival_hour: int | None
    night_shift_flag: bool | None
    weekend_flag: bool | None

    acuity: int | None

    predicted_high_acuity: bool | None
    predicted_probability: float | None
    model_version: str | None
    scored_at: datetime | None


class TriageStayPage(BaseModel):
    """Paginated list response."""

    total: int
    limit: int
    offset: int
    items: list[TriageStayOut]


class TriageStaySummary(BaseModel):
    """
    Aggregate counts for the dashboard — computed in SQL/pandas, not
    guessed. Every field here answers a question a nurse or reviewer
    would actually ask about this cohort.
    """

    total_stays: int
    untriaged_count: int
    acuity_counts: dict[str, int]
    age_group_counts: dict[str, int]
    arrival_transport_counts: dict[str, int]
    disposition_counts: dict[str, int]
    zero_vitals_count: int
    missing_history_count: int
    scored_count: int
    predicted_high_acuity_count: int
    data_quality_notes: list[str]
