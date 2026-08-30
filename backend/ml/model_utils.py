"""
ml/model_utils.py
====================

PatientTriage.ai — Shared Model Utilities
-----------------------------------------------
`build_features()` is the SINGLE place a patient dict becomes a feature
vector. `train_model.py` and `predict.py` both call it — nothing else in
either module builds features independently. This is a hard lesson from
this project's own history: an earlier model trained on pre-scaled CSV
columns while serving on raw values, and a scaler fit on already-scaled
training data silently saturated almost every live prediction. Sharing
one function removes the possibility of that class of bug recurring.

Missing values are never silently treated as normal. A missing vital
contributes 0.0 to its own feature (the same convention `ml/train.py`
already uses) AND is counted in `vitals_missing_count`, which both the
model and `uncertainty.py`'s missing-data penalty can see.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import get_logger
from ml.rule_engine import band_for_age

logger = get_logger(__name__)

KNOWN_TRANSPORTS = ["AMBULANCE", "OTHER", "UNKNOWN", "WALK IN"]
KNOWN_GENDERS = ["F", "M"]

VITAL_KEYS = ["temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp", "pain"]

# Feature order is part of the model contract — persisted alongside the
# artifact and validated on load, so a mismatched schema fails loudly at
# startup rather than silently mis-scoring patients.
FEATURE_NAMES = [
    "age", "age_group_pediatric", "age_group_geriatric",
    "shock_index", "pulse_pressure", "mean_arterial_pressure",
    "temperature_c", "heartrate", "resprate", "o2sat", "sbp", "dbp", "pain",
    "abnormal_vitals_count", "vitals_missing_count", "missing_history_flag",
    "arrival_hour", "night_shift", "weekend_flag",
] + [f"arrival_transport_{t}" for t in KNOWN_TRANSPORTS] + [f"gender_{g}" for g in KNOWN_GENDERS]


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _to_celsius(temp_f_or_c: float | None) -> float | None:
    """Source data is Fahrenheit; a value <= 50 is already Celsius (defensive, not assumed)."""
    if temp_f_or_c is None:
        return None
    return (temp_f_or_c - 32) * 5 / 9 if temp_f_or_c > 50 else temp_f_or_c


def build_features(patient: dict) -> dict[str, float]:
    """
    Convert one patient dict into the exact feature vector the model
    consumes. Accepts either the MIMIC-style keys (`heartrate`, `o2sat`,
    `resprate`) used by the incoming API contract, or the readable
    `TriageStay` keys (`heart_rate`, `o2_sat`, `resp_rate`) — both are
    checked so this function works whether the caller is `predict.py`
    scoring a fresh API request or a training row loaded from the
    database.

    Every numeric feature defaults to 0.0 when missing. This is a
    convention, not an assumption of normality — `vitals_missing_count`
    and `missing_history_flag` make the gap visible to both the model
    and the uncertainty layer, which is where "missing data increases
    uncertainty" is actually enforced (see `uncertainty.py`).

    Returns
    -------
    dict[str, float]
        Keyed by `FEATURE_NAMES`. Always contains every key.
    """
    age = _num(patient.get("age"))
    band = band_for_age(age)

    hr = _num(patient.get("heartrate", patient.get("heart_rate")))
    rr = _num(patient.get("resprate", patient.get("resp_rate")))
    sbp = _num(patient.get("sbp"))
    dbp = _num(patient.get("dbp"))
    spo2 = _num(patient.get("o2sat", patient.get("o2_sat", patient.get("spo2"))))
    temp_raw = _num(patient.get("temperature"))
    temp_c = _to_celsius(temp_raw)
    pain = _num(patient.get("pain"))

    shock_index = (hr / sbp) if (hr is not None and sbp not in (None, 0)) else None
    pulse_pressure = (sbp - dbp) if (sbp is not None and dbp is not None) else None
    map_value = (dbp + (sbp - dbp) / 3.0) if (sbp is not None and dbp is not None) else None

    abnormal = 0
    for value, lo, hi in ((hr, *band.hr), (rr, *band.rr), (sbp, *band.sbp)):
        if value is not None and (value < lo or value > hi):
            abnormal += 1
    if spo2 is not None and spo2 < band.spo2_floor:
        abnormal += 1

    missing_vitals = sum(1 for v in (temp_raw, hr, rr, spo2, sbp, dbp, pain) if v is None)

    complaint = str(patient.get("chief_complaint", patient.get("chiefcomplaint", "")) or "").strip()
    missing_history = 1.0 if not complaint else 0.0

    arrival_hour = _num(patient.get("arrival_hour"))
    night_shift = float(patient.get("night_shift_flag", 0) or 0)
    if arrival_hour is not None and patient.get("night_shift_flag") is None:
        night_shift = 1.0 if (arrival_hour >= 23 or arrival_hour < 7) else 0.0
    weekend = float(patient.get("weekend_flag", 0) or 0)

    transport = str(patient.get("arrival_transport", "UNKNOWN") or "UNKNOWN").upper()
    if transport not in KNOWN_TRANSPORTS:
        transport = "OTHER"

    gender = str(patient.get("gender", "") or "").upper()
    gender = gender if gender in KNOWN_GENDERS else None

    features = {
        "age": age or 0.0,
        "age_group_pediatric": 1.0 if age is not None and age < 18 else 0.0,
        "age_group_geriatric": 1.0 if age is not None and age >= 65 else 0.0,
        "shock_index": shock_index or 0.0,
        "pulse_pressure": pulse_pressure or 0.0,
        "mean_arterial_pressure": map_value or 0.0,
        "temperature_c": temp_c or 0.0,
        "heartrate": hr or 0.0,
        "resprate": rr or 0.0,
        "o2sat": spo2 or 0.0,
        "sbp": sbp or 0.0,
        "dbp": dbp or 0.0,
        "pain": pain or 0.0,
        "abnormal_vitals_count": float(abnormal),
        "vitals_missing_count": float(missing_vitals),
        "missing_history_flag": missing_history,
        "arrival_hour": arrival_hour or 0.0,
        "night_shift": night_shift,
        "weekend_flag": weekend,
    }
    for t in KNOWN_TRANSPORTS:
        features[f"arrival_transport_{t}"] = 1.0 if transport == t else 0.0
    for g in KNOWN_GENDERS:
        features[f"gender_{g}"] = 1.0 if gender == g else 0.0

    return features


def features_to_row(features: dict[str, float]) -> pd.DataFrame:
    """Order a feature dict into the model's expected column order as a single-row frame."""
    return pd.DataFrame([{k: features.get(k, 0.0) for k in FEATURE_NAMES}], columns=FEATURE_NAMES)


def load_labeled_stays(min_class_size: int = 10) -> tuple[pd.DataFrame, "pd.Series", list[int]]:
    """
    Pull every triaged `TriageStay` from the database and build the
    feature matrix via `build_features()` — the SAME function used at
    inference time. Classes with fewer than `min_class_size` examples
    are excluded and logged, never silently mixed in (see
    `ml/train_model.py`'s module docstring for why: 2 examples cannot
    inform a class boundary).

    Shared by `train_model.py` and `explain.py` so evaluation always
    sees exactly the data the model was trained on — an earlier version
    of this pattern duplicated this loading logic in two places and the
    two copies drifted, which is exactly the class of bug this function
    exists to prevent.

    Returns
    -------
    X : pd.DataFrame
        Feature matrix, columns = FEATURE_NAMES.
    y : pd.Series
        TRUE priority labels (e.g. 1/2/3) — NOT remapped to 0..n-1.
        Callers that need zero-indexed labels for XGBoost (see
        `train_model.py::train`) must remap themselves; keeping the raw
        priority labels here keeps this function's output meaningful on
        its own.
    classes : list[int]
        Sorted ascending list of trainable priority levels.
    """
    from app.core.database import SessionLocal
    from app.models.triage_stay import TriageStay

    db = SessionLocal()
    try:
        stays = db.query(TriageStay).filter(TriageStay.acuity.is_not(None)).all()
        counts = pd.Series([s.acuity for s in stays]).value_counts().to_dict()
        trainable_classes = sorted(c for c, n in counts.items() if n >= min_class_size)
        excluded_classes = sorted(set(counts) - set(trainable_classes))

        rows, labels, excluded_n = [], [], 0
        for stay in stays:
            if stay.acuity not in trainable_classes:
                excluded_n += 1
                continue
            patient = {
                "age": None,  # absent from this MIMIC-IV-ED demo extract — see README
                "gender": stay.gender,
                "heartrate": stay.heart_rate,
                "resprate": stay.resp_rate,
                "sbp": stay.sbp,
                "dbp": stay.dbp,
                "temperature": stay.temperature,
                "o2sat": stay.o2_sat,
                "pain": stay.pain,
                "chief_complaint": stay.chief_complaint,
                "arrival_transport": stay.arrival_transport,
                "night_shift_flag": stay.night_shift_flag,
                "weekend_flag": stay.weekend_flag,
                "arrival_hour": stay.arrival_hour,
            }
            rows.append(build_features(patient))
            labels.append(int(stay.acuity))

        if excluded_n:
            logger.warning(
                "Excluded %d stays with acuity in %s from training/evaluation — fewer than "
                "%d examples is not enough to learn a class boundary. See train_model.py's "
                "module docstring.",
                excluded_n, excluded_classes, min_class_size,
            )

        X = pd.DataFrame(rows, columns=FEATURE_NAMES)
        y = pd.Series(labels, name="acuity")
        return X, y, trainable_classes
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Model artifact I/O
# --------------------------------------------------------------------------- #
ARTIFACT_NAME = "triage_ensemble.joblib"
METRICS_NAME = "triage_ensemble_metrics.json"


@dataclass
class ModelArtifact:
    """Everything `predict.py` needs, saved and loaded as one object."""

    base_models: dict  # name -> fitted classifier
    meta_learner: object  # fitted LogisticRegression stacking head
    calibrators: dict  # name -> fitted CalibratedClassifierCV (or None)
    classes: list[int]  # e.g. [1, 2, 3] — priority levels the ensemble was trained on
    feature_names: list[str]
    version: str
    metrics: dict


def save_artifact(artifact: ModelArtifact, reports_dir: Path | None = None) -> Path:
    settings = get_settings()
    reports_dir = reports_dir or settings.REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    path = reports_dir / ARTIFACT_NAME
    joblib.dump(artifact, path)

    metrics_path = reports_dir / METRICS_NAME
    metrics_path.write_text(json.dumps(artifact.metrics, indent=2, default=str))

    logger.info("Saved ensemble artifact to %s", path)
    return path


def load_artifact(reports_dir: Path | None = None) -> ModelArtifact | None:
    settings = get_settings()
    reports_dir = reports_dir or settings.REPORTS_DIR
    path = reports_dir / ARTIFACT_NAME

    if not path.exists():
        logger.warning("No trained ensemble found at %s. Run `python -m ml.train_model`.", path)
        return None

    try:
        artifact: ModelArtifact = joblib.load(path)
    except Exception as exc:  # noqa: BLE001 — a corrupt artifact must not crash the app
        logger.error("Failed to load ensemble artifact at %s: %s", path, exc)
        return None

    if artifact.feature_names != FEATURE_NAMES:
        logger.error(
            "Loaded artifact's feature schema does not match the current build_features() "
            "output. The model was trained against a different feature contract — "
            "retrain with `python -m ml.train_model` before serving. Refusing to load."
        )
        return None

    return artifact
