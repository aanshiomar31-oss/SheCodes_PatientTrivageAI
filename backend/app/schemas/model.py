"""
schemas/model.py
===================

PatientTriage.ai — Model Endpoint Schemas
-----------------------------------------------
Response models for `GET/POST /api/v1/model/*`.
"""

from __future__ import annotations

from pydantic import BaseModel


class ModelStatus(BaseModel):
    available: bool
    version: str | None
    threshold: float | None
    feature_count: int
    note: str | None = None


class StayPrediction(BaseModel):
    """A recommendation only — see the governing rule in api/routes/model.py."""

    stay_id: int
    high_acuity: bool
    probability: float
    threshold: float
    model_version: str
    top_features: list[dict]
    governing_rule: str = "The AI recommends. The nurse decides."


class BatchScoreResult(BaseModel):
    scored: int
    skipped_already_scored: int
    model_version: str


class FeatureImportanceOut(BaseModel):
    version: str | None
    method: str | None
    feature_importance: list[list]
