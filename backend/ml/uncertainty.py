"""
ml/uncertainty.py
====================

PatientTriage.ai — Confidence System
-------------------------------------------
Combines three independent signals into one confidence score. This is
mandatory infrastructure, not a nice-to-have: the platform's design
principle is that missing data increases uncertainty, and a bare
softmax probability cannot express that on its own — a model can be
"confident" in the sense of a peaked probability while having been
given almost no information to be confident about.

Three signals
----------------
1. Calibrated probability — how strongly the calibrated stack favors
   its top class.
2. Ensemble agreement — whether the base learners (XGBoost, LightGBM,
   CatBoost, HistGradientBoosting) actually agree with each other.
   Agreement is computed from the SAME fitted base models saved by
   `train_model.py`, not retrained here.
3. Missing-data penalty — vitals and history that were never recorded
   subtract from confidence directly, independent of what the model's
   probability says, because a model has no way to "know what it
   doesn't know" from a zero-filled feature alone.

Confidence never OVERRULES a rule-engine escalation. If the rule engine
fired, `ml/predict.py` reports confidence for context, but the priority
itself is already floored by the rule — see that module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from ml.model_utils import ModelArtifact, features_to_row

logger = get_logger(__name__)

# Weights sum to 1.0. Missing-data penalty carries real weight rather than
# being a minor tiebreaker — under-confidence from incomplete data is the
# platform's explicit design intent, not an edge case.
WEIGHT_PROBABILITY = 0.50
WEIGHT_AGREEMENT = 0.30
WEIGHT_COMPLETENESS = 0.20

# Fields checked for the missing-data penalty, and the human-readable
# reason surfaced when each is absent — used to build `uncertainty_reason`.
MISSING_DATA_CHECKS: list[tuple[str, str]] = [
    ("vitals_missing_count", "vitals"),  # handled specially: proportional, not binary
    ("missing_history_flag", "chief complaint / presenting history"),
]


@dataclass
class ConfidenceResult:
    confidence: float
    uncertainty_reason: str | None
    components: dict

    def to_dict(self) -> dict:
        return {
            "confidence": self.confidence,
            "uncertainty_reason": self.uncertainty_reason,
            "components": self.components,
        }


def _ensemble_agreement(artifact: ModelArtifact, row: pd.DataFrame) -> float:
    """
    Fraction of base learners that agree with the majority-voted class
    for this single patient. 1.0 = unanimous, lower = the base models
    disagree with each other — a signal a single calibrated probability
    cannot see, since a stack can be confident even when its inputs
    disagree if the meta-learner has learned to trust one of them.
    """
    if not artifact.base_models:
        return 1.0  # no base models saved (shouldn't happen) — do not fabricate disagreement

    votes = [int(np.asarray(model.predict(row)).ravel()[0]) for model in artifact.base_models.values()]
    votes_arr = np.array(votes)
    _, counts = np.unique(votes_arr, return_counts=True)
    return float(counts.max() / len(votes_arr))


def _missing_data_penalty(features: dict[str, float], patient: dict) -> tuple[float, list[str]]:
    """
    Returns a penalty in [0, 1] (0 = nothing missing) and the specific
    reasons contributing to it, so `uncertainty_reason` names the actual
    gap rather than a generic "data incomplete".
    """
    reasons: list[str] = []
    penalty = 0.0

    n_missing_vitals = features.get("vitals_missing_count", 0.0)
    if n_missing_vitals > 0:
        # Proportional: 1 missing vital is a small penalty, most/all missing
        # is a large one — matches "missing data increases uncertainty"
        # without letting one absent field alone dominate the score.
        penalty += min(0.5, n_missing_vitals / 7.0 * 0.5)
        reasons.append(
            f"{int(n_missing_vitals)} vital sign(s) not recorded"
            if n_missing_vitals > 1 else "1 vital sign not recorded"
        )

    if features.get("missing_history_flag", 0.0) >= 1.0:
        penalty += 0.20
        reasons.append("Missing chief complaint / presenting history")

    if patient.get("history") is None and patient.get("zero_history") is not False:
        # Explicit zero-history flag, distinct from a merely-blank complaint.
        if patient.get("zero_history") is True:
            penalty += 0.15
            reasons.append("No prior medical history on file")

    if not patient.get("medications") and patient.get("medications") is not None:
        pass  # empty list is a documented "no medications", not missing data — no penalty
    elif "medications" not in patient:
        penalty += 0.05
        reasons.append("Medication history not provided")

    return min(1.0, penalty), reasons


def estimate_confidence(
    artifact: ModelArtifact,
    patient: dict,
    features: dict[str, float],
    predicted_class: int,
    class_probabilities: dict[int, float],
) -> ConfidenceResult:
    """
    Compute the final confidence score for one prediction.

    Parameters
    ----------
    artifact : ModelArtifact
        The loaded ensemble, including fitted base models for the
        agreement signal.
    patient : dict
        The original patient input, used for missing-data checks that
        the numeric feature vector alone can't distinguish (e.g. an
        explicit `zero_history` flag vs. simply no complaint text).
    features : dict[str, float]
        Output of `ml.model_utils.build_features(patient)`.
    predicted_class : int
        The class the ensemble's calibrated probability favors.
    class_probabilities : dict[int, float]
        Full calibrated probability distribution over trained classes.

    Returns
    -------
    ConfidenceResult
    """
    calibrated_prob = float(class_probabilities.get(predicted_class, 0.0))

    row = features_to_row(features)
    agreement = _ensemble_agreement(artifact, row)

    penalty, reasons = _missing_data_penalty(features, patient)
    completeness = 1.0 - penalty

    confidence = (
        WEIGHT_PROBABILITY * calibrated_prob
        + WEIGHT_AGREEMENT * agreement
        + WEIGHT_COMPLETENESS * completeness
    )
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    # Report the single most informative reason, not every contributing
    # factor — a nurse needs "why is this uncertain", not a debug dump.
    uncertainty_reason = None
    if reasons:
        uncertainty_reason = reasons[0]
    elif agreement < 0.75:
        uncertainty_reason = "Base models disagree on this patient's acuity"
    elif calibrated_prob < 0.55:
        uncertainty_reason = "Model probability is not strongly peaked on any single priority"

    logger.debug(
        "Confidence=%.4f (prob=%.4f agreement=%.4f completeness=%.4f) reason=%s",
        confidence, calibrated_prob, agreement, completeness, uncertainty_reason,
    )

    return ConfidenceResult(
        confidence=confidence,
        uncertainty_reason=uncertainty_reason,
        components={
            "calibrated_probability": round(calibrated_prob, 4),
            "ensemble_agreement": round(agreement, 4),
            "data_completeness": round(completeness, 4),
            "missing_data_reasons": reasons,
        },
    )
