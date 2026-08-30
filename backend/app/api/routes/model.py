"""
api/routes/model.py
======================

PatientTriage.ai — Model Endpoints
---------------------------------------
Serves recommendations from the artifact trained by `ml/train.py`
(loaded via `app.ml.model_registry`). Every endpoint here is read-only
with respect to clinical state except `/model/score-all`, which writes
`predicted_high_acuity` — a recommendation field, never the acuity of
record — onto `triage_stays`.

Governing rule: "The AI recommends. The nurse decides." No route in
this module moves a patient in a queue or overrides `acuity` (the
ground-truth/clinically-assigned field). A prediction is always
reviewable: it is visible on the stay record alongside, never in place
of, the original triage data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.ml.model_registry import ModelRegistry, get_model_registry
from app.models.triage_stay import TriageStay
from app.schemas.model import BatchScoreResult, FeatureImportanceOut, ModelStatus, StayPrediction

router = APIRouter(prefix="/model", tags=["model"])
logger = get_logger(__name__)


def _stay_to_features(stay: TriageStay) -> dict[str, float]:
    """
    The SINGLE place a `TriageStay` row is converted into the feature
    vector the model expects. Both `/model/predict/{stay_id}` and
    `/model/score-all` call this, so train/serve feature construction
    can never silently diverge between the two call sites.

    Mirrors `ml/preprocess.py`'s feature engineering exactly:
    `night_shift_flag`/`weekend_flag` default to 0 when unknown (rather
    than being dropped) since the model was trained on the same
    zero-filled convention (`ml/train.py::load_training_frame`).
    `arrival_transport` is one-hot encoded to match the training columns.
    """
    transport = (stay.arrival_transport or "UNKNOWN").upper()
    known_transports = {"AMBULANCE", "OTHER", "UNKNOWN", "WALK IN"}
    if transport not in known_transports:
        transport = "OTHER"

    features = {
        "missing_history_flag": float(stay.missing_history_flag),
        "night_shift_flag": float(stay.night_shift_flag or 0),
        "weekend_flag": float(stay.weekend_flag or 0),
        "temperature": stay.temperature or 0.0,
        "heartrate": stay.heart_rate or 0.0,
        "resprate": stay.resp_rate or 0.0,
        "o2sat": stay.o2_sat or 0.0,
        "sbp": stay.sbp or 0.0,
        "dbp": stay.dbp or 0.0,
        "pain": stay.pain or 0.0,
        "shock_index": stay.shock_index or 0.0,
        "pulse_pressure": stay.pulse_pressure or 0.0,
        "mean_arterial_pressure": stay.mean_arterial_pressure or 0.0,
        "abnormal_vitals_count": float(stay.abnormal_vitals_count),
        "vitals_missing_count": float(stay.vitals_missing_count),
        "arrival_hour": float(stay.arrival_hour or 0),
    }
    for t in known_transports:
        features[f"arrival_transport_{t}"] = 1.0 if transport == t else 0.0

    return features


@router.get("/status", response_model=ModelStatus)
def model_status(registry: ModelRegistry = Depends(get_model_registry)) -> ModelStatus:
    """Whether a trained model is available, and which one."""
    if not registry.available:
        return ModelStatus(
            available=False, version=None, threshold=None, feature_count=0,
            note="No trained model found. Run `python -m ml.train` from backend/.",
        )
    return ModelStatus(
        available=True, version=registry.version, threshold=registry.threshold,
        feature_count=len(registry.feature_names),
    )


@router.get("/feature-importance", response_model=FeatureImportanceOut)
def feature_importance(registry: ModelRegistry = Depends(get_model_registry)) -> FeatureImportanceOut:
    """Global feature importance (SHAP, or permutation-importance fallback) from the last training run."""
    if not registry.available or registry.feature_importance is None:
        raise HTTPException(status_code=404, detail="No feature importance available. Run `python -m ml.train`.")
    return FeatureImportanceOut(
        version=registry.version, method="shap", feature_importance=registry.feature_importance,
    )


@router.post("/predict/{stay_id}", response_model=StayPrediction)
def predict_stay(
    stay_id: int, db: Session = Depends(get_db), registry: ModelRegistry = Depends(get_model_registry),
) -> StayPrediction:
    """
    Score one stay on demand. Does NOT persist the result — this is the
    "what would the model say right now" endpoint, distinct from
    `/model/score-all`, which writes the recommendation onto the record.
    """
    if not registry.available:
        raise HTTPException(status_code=503, detail="No trained model available. Run `python -m ml.train`.")

    stay = db.get(TriageStay, stay_id)
    if stay is None:
        raise HTTPException(status_code=404, detail=f"No triage stay with stay_id={stay_id}")

    features = _stay_to_features(stay)
    result = registry.predict(features)

    return StayPrediction(
        stay_id=stay_id, high_acuity=result.high_acuity, probability=result.probability,
        threshold=result.threshold, model_version=result.model_version, top_features=result.top_features,
    )


@router.post("/score-all", response_model=BatchScoreResult)
def score_all_stays(
    force: bool = False,
    db: Session = Depends(get_db),
    registry: ModelRegistry = Depends(get_model_registry),
) -> BatchScoreResult:
    """
    Batch-score every stay and write `predicted_high_acuity` +
    `predicted_probability` + `model_version` + `scored_at` onto each
    `TriageStay` row, so the dashboard can filter/sort by recommendation
    without a per-row inference call.

    This WRITES to the database — the only route in this module that
    does. It never touches `acuity` (the clinically assigned ground
    truth): the recommendation lives in separate `predicted_*` columns,
    always alongside the original data, never in place of it.

    `force=False` (default) skips stays already scored by the current
    model version, so re-running after a restart is cheap and idempotent.
    """
    if not registry.available:
        raise HTTPException(status_code=503, detail="No trained model available. Run `python -m ml.train`.")

    stmt = select(TriageStay)
    if not force:
        stmt = stmt.where(
            (TriageStay.model_version.is_(None)) | (TriageStay.model_version != registry.version)
        )
    stays = db.execute(stmt).scalars().all()
    total = db.execute(select(TriageStay.stay_id)).scalars().all()
    skipped = len(total) - len(stays)

    now = datetime.now(timezone.utc)
    for stay in stays:
        features = _stay_to_features(stay)
        result = registry.predict(features)
        stay.predicted_high_acuity = result.high_acuity
        stay.predicted_probability = result.probability
        stay.model_version = result.model_version
        stay.scored_at = now

    db.commit()
    logger.info("Batch-scored %d stays with model %s (%d already up to date, skipped)",
                len(stays), registry.version, skipped)

    return BatchScoreResult(scored=len(stays), skipped_already_scored=skipped, model_version=registry.version)


@router.post("/reload")
def reload_model(registry: ModelRegistry = Depends(get_model_registry)) -> ModelStatus:
    """Pick up a newly trained artifact without restarting the API process."""
    registry.reload()
    return model_status(registry)
