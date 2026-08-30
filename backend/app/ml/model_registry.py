"""
app/ml/model_registry.py
============================

PatientTriage.ai — Model Registry (Inference Surface)
------------------------------------------------------------
Thin, app-facing wrapper around the artifact produced by
`ml/train.py` (`reports/model.joblib`). This module is what the FastAPI
app imports; it contains no training logic of its own — training lives
in `backend/ml/` alongside the data pipeline it depends on
(`data_loader.py`, `features.py`, `preprocess.py`), while this module is
the runtime-facing "load it and serve it" surface the README originally
reserved `app/ml/` for.

Governing rule: "The AI recommends. The nurse decides." A prediction
from this module is a recommendation only — nothing here writes to the
triage queue, moves a patient, or bypasses review. See
`api/routes/model.py` for how predictions are surfaced and logged.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import joblib
import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()


@dataclass
class Prediction:
    high_acuity: bool
    probability: float
    threshold: float
    model_version: str
    top_features: list[dict]


class ModelRegistry:
    """
    Loads and caches the trained artifact. `available` is False (never
    raises) when no model has been trained yet, so the app can start and
    serve `/triage-stays` even before `python -m ml.train` has run —
    a missing model degrades one feature, it does not crash the API.
    """

    def __init__(self) -> None:
        self._bundle: dict | None = None
        self._loaded_at: datetime | None = None
        self._feature_importance: list[list] | None = None
        self._reload()

    def _reload(self) -> None:
        settings = get_settings()
        model_path = settings.REPORTS_DIR / "model.joblib"
        importance_path = settings.REPORTS_DIR / "feature_importance.json"

        if not model_path.exists():
            logger.warning(
                "No trained model found at %s. Run `python -m ml.train` from backend/ "
                "to enable /api/v1/model/* endpoints.", model_path,
            )
            self._bundle = None
            return

        try:
            self._bundle = joblib.load(model_path)
            self._loaded_at = datetime.now(timezone.utc)
            logger.info(
                "Loaded model %s (%d features) from %s",
                self._bundle["version"], len(self._bundle["feature_names"]), model_path,
            )
        except Exception as exc:  # noqa: BLE001 — a corrupt artifact must not crash the app
            logger.error("Failed to load model artifact at %s: %s", model_path, exc)
            self._bundle = None
            return

        if importance_path.exists():
            import json
            try:
                self._feature_importance = json.loads(importance_path.read_text())["feature_importance"]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load feature_importance.json: %s", exc)
                self._feature_importance = None

    def reload(self) -> None:
        """Public hook to pick up a newly trained artifact without restarting the app."""
        with _lock:
            self._reload()

    @property
    def available(self) -> bool:
        return self._bundle is not None

    @property
    def version(self) -> str | None:
        return self._bundle["version"] if self._bundle else None

    @property
    def feature_names(self) -> list[str]:
        return list(self._bundle["feature_names"]) if self._bundle else []

    @property
    def threshold(self) -> float | None:
        return self._bundle["threshold"] if self._bundle else None

    @property
    def feature_importance(self) -> list[list] | None:
        return self._feature_importance

    def predict(self, features: dict[str, float]) -> Prediction:
        """
        Score one stay. `features` must be keyed by the exact feature
        names the model was trained on (see `self.feature_names`) —
        callers build this from a `TriageStay` row via
        `app/api/routes/model.py::_stay_to_features`, which is the single
        place train/serve feature construction is kept in sync.

        Missing keys are filled with 0.0 (the value a scaled/one-hot
        column takes when a category or flag is absent) rather than
        raising, so a partially-documented stay still gets scored — with
        the resulting reduced information reflected in the probability,
        not in a crash.
        """
        if self._bundle is None:
            raise RuntimeError("No trained model available. Run `python -m ml.train` first.")

        row = {name: float(features.get(name, 0.0)) for name in self._bundle["feature_names"]}
        X = pd.DataFrame([row], columns=self._bundle["feature_names"])

        proba = float(self._bundle["model"].predict_proba(X)[0, 1])
        threshold = float(self._bundle["threshold"])

        top_features = sorted(
            ({"feature": k, "value": v} for k, v in row.items() if v != 0.0),
            key=lambda d: -abs(d["value"]),
        )[:5]

        return Prediction(
            high_acuity=proba >= threshold,
            probability=round(proba, 4),
            threshold=threshold,
            model_version=self._bundle["version"],
            top_features=top_features,
        )


@lru_cache
def get_model_registry() -> ModelRegistry:
    """FastAPI dependency-friendly singleton accessor."""
    return ModelRegistry()
