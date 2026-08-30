"""
ml/train.py
=============

PatientTriage.ai — Milestone 3: Model Training
---------------------------------------------------
Trains a high-acuity triage classifier on the same clinically-readable
ED-stay data `triage_stays` is loaded from (`ml.preprocess.build_readable_frame`),
in raw clinical units — NOT on the pre-scaled `data/processed_triage.csv`.
See the NUMERIC_FEATURES comment below for why: an earlier version of
this module trained on the scaled CSV and served on raw `TriageStay`
values, which silently saturated nearly every prediction. Training and
serving now share one raw-unit feature contract.

Why binary, not the original 5-level acuity scale
------------------------------------------------------
The labeled cohort is small (207 stays) and severely imbalanced across
5 classes: acuity 1=18, 2=97, 3=90, 4=2, 5=0. A 5-class model trained on
2 examples of one class is not a model, it is noise with a name. This
platform's own governing principle — under-triage is worse than
over-triage — gives a natural, clinically meaningful binary collapse:

    high_acuity = acuity in {1, 2}   (needs urgent review)
    lower_acuity = acuity in {3, 4}  (can safely wait longer)

That's 115 vs 92 — small, but usable. If a future data refresh brings a
larger, better-balanced cohort, the 5-class problem is worth revisiting;
forcing it today would produce a model that looks precise and isn't.

Feature exclusions (deliberate, not oversights)
----------------------------------------------------
* `disposition_*` — recorded when the ED stay ENDS (admitted / home /
  transferred), hours after triage acuity is assigned. Including it
  would let the model see the future. Excluded as temporal leakage.
* `race_*`, `gender_*` — protected attributes. Excluded from the
  feature set on clinical-ethics grounds (a triage acuity score should
  not be a function of race or gender), but RETAINED for the post-hoc
  fairness check this module runs after training — excluding a
  variable from the model does not exempt the model from being checked
  for disparate impact across it.
* `age_group_Unknown` — constant (1.0 for all 207 rows, since the
  source data has no `anchor_age`). Zero information; including it only
  adds noise to feature-importance output.

Evaluation strategy
-----------------------
207 labeled rows is too few for a single held-out test split to be
trustworthy — a "lucky" or "unlucky" split would swing every metric.
Every model is instead evaluated by repeated stratified cross-validation
with out-of-fold predictions, and the deployed model is refit on the
full labeled cohort. Reported metrics are cross-validated, not
held-out-test, and this module says so in its own output rather than
letting a stray "test accuracy" number imply otherwise.

Cost-sensitive threshold
----------------------------
Consistent with the platform's asymmetric-cost principle, the decision
threshold is chosen to minimize (missed_high_acuity * UNDER_TRIAGE_COST
+ false_alarm * OVER_TRIAGE_COST) on out-of-fold predictions, subject to
an alert-rate ceiling relative to prevalence — an unconstrained cost
search degenerates to "flag everyone," which is safe on paper and
useless in a department, since nurses stop reading a tool that alarms
on every patient.

Run:
    cd backend
    python -m ml.train
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Cost model (mirrors the clinical-safety principle stated throughout this
# platform: missing a high-acuity patient is far worse than a false alarm).
# --------------------------------------------------------------------------- #
UNDER_TRIAGE_COST = 15.0
OVER_TRIAGE_COST = 1.0

# A model tuned purely on the cost above degenerates to alarming on
# everyone. The ceiling caps alerts at this multiple of true prevalence,
# with an absolute cap regardless of prevalence: flagging 80%+ of an
# entire ED as "high acuity" provides a nurse no triage information even
# if technically cost-minimizing, since it fails to separate anyone from
# anyone else.
MAX_ALERT_MULTIPLE = 1.3
ALERT_RATE_FLOOR = 0.20
ALERT_RATE_CEILING = 0.65

LABEL_COLUMN = "acuity"
HIGH_ACUITY_LEVELS = (1, 2)

# Raw-unit feature schema. This list is the SINGLE contract between
# training and serving: app/api/routes/model.py::_stay_to_features builds
# exactly these keys from a TriageStay row, in the same units. Training
# on the pre-scaled processed_triage.csv and serving on raw TriageStay
# values previously caused a severe train/serve skew (a StandardScaler
# fit on already-standardized data, then fed genuinely raw values at
# inference, saturated almost every prediction to ~1.0) — caught via the
# end-to-end smoke test, not by inspection. Training on this raw schema
# and letting each candidate's own pipeline (StandardScaler for the
# logistic baseline; tree models need no scaling) do the ONE real scale
# transform removes the mismatch entirely rather than papering over it.
NUMERIC_FEATURES = [
    "temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp", "pain",
    "shock_index", "pulse_pressure", "mean_arterial_pressure",
    "abnormal_vitals_count", "vitals_missing_count", "arrival_hour",
]
FLAG_FEATURES = ["missing_history_flag", "night_shift_flag", "weekend_flag"]
KNOWN_TRANSPORTS = ["AMBULANCE", "OTHER", "UNKNOWN", "WALK IN"]

N_SPLITS = 5
N_REPEATS = 5
RANDOM_STATE = 42


@dataclass
class TrainedModel:
    name: str
    estimator: object
    cv_probabilities: np.ndarray  # out-of-fold P(high_acuity), one per labeled row
    metrics: dict


def _feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in NUMERIC_FEATURES + FLAG_FEATURES if c in df.columns] + [
        f"arrival_transport_{t}" for t in KNOWN_TRANSPORTS
    ]


def load_training_frame() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """
    Build the training frame from the same READABLE (raw-unit) source
    the database is loaded from (`ml.preprocess.build_readable_frame`),
    NOT from `data/processed_triage.csv`. See NUMERIC_FEATURES' docstring
    comment above for why: training on the pre-scaled CSV while serving
    on raw `TriageStay` values caused a severe, silently-wrong prediction
    skew. `processed_triage.csv` remains the artifact `load_triage_stays.py`
    and ad-hoc analysis use; this module has its own raw-unit contract
    that matches `app/api/routes/model.py::_stay_to_features` exactly.

    Feature exclusions (deliberate, not oversights)
    ----------------------------------------------------
    * `disposition` — recorded when the ED stay ENDS, hours after triage
      acuity is assigned. Including it would let the model see the
      future. Excluded as temporal leakage.
    * `race`, `gender` — protected attributes. Excluded from the feature
      set on clinical-ethics grounds, but RETAINED for the post-hoc
      fairness check this module runs after training.
    * `age_group` — constant ("Unknown") for every row in this data
      extract (no `anchor_age` in the source), so it carries zero
      information; included as a feature it would only add noise.

    Returns
    -------
    X : pd.DataFrame
        Feature matrix, raw clinical units, one-hot arrival_transport.
    y : pd.Series
        Binary target, 1 = high acuity (MIMIC acuity 1 or 2).
    feature_names : list[str]
        Column order, persisted alongside the model.
    """
    from ml.preprocess import build_readable_frame

    df = build_readable_frame()
    n_total = len(df)

    labeled = df.dropna(subset=[LABEL_COLUMN]).copy()
    n_unlabeled = n_total - len(labeled)
    if n_unlabeled:
        logger.warning(
            "%d/%d stays have no recorded acuity and are excluded from supervised "
            "training (kept visible for nurse review via /triage-stays, never dropped "
            "from the database — only from this training set).",
            n_unlabeled, n_total,
        )

    y = labeled[LABEL_COLUMN].astype(int).isin(HIGH_ACUITY_LEVELS).astype(int)

    transport = labeled.get("arrival_transport", pd.Series(index=labeled.index, dtype=object))
    transport = transport.fillna("UNKNOWN").str.upper()
    transport = transport.where(transport.isin(KNOWN_TRANSPORTS), "OTHER")
    for t in KNOWN_TRANSPORTS:
        labeled[f"arrival_transport_{t}"] = (transport == t).astype(float)

    for flag in FLAG_FEATURES:
        if flag in labeled.columns:
            labeled[flag] = labeled[flag].fillna(0).astype(float)

    feature_names = _feature_columns(labeled)
    X = labeled[feature_names].copy()

    if X.isna().any().any():
        n_na = int(X.isna().sum().sum())
        logger.info("%d missing vital values in feature matrix — filled with 0 (matches serving convention).", n_na)
        X = X.fillna(0.0)

    logger.info(
        "Training frame: %d labeled stays, %d features (raw units, matches serving contract), "
        "high_acuity prevalence=%.3f",
        len(X), len(feature_names), float(y.mean()),
    )
    return X, y, feature_names


def _build_candidates(random_state: int = RANDOM_STATE) -> dict:
    """
    Baseline models (must be beaten to justify the extra complexity of an
    ensemble) plus the boosted-ensemble field. Deliberately shallow/
    regularized throughout — 207 rows overfits fast.
    """
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    candidates = {
        "baseline_majority_class": DummyClassifier(strategy="most_frequent"),
        "baseline_logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced",
                               random_state=random_state),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=4,
            class_weight="balanced", random_state=random_state, n_jobs=-1,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=150, max_depth=3, learning_rate=0.08, random_state=random_state,
        ),
    }

    try:
        from xgboost import XGBClassifier
        candidates["xgboost"] = XGBClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.08,
            subsample=0.85, colsample_bytree=0.85, eval_metric="logloss",
            random_state=random_state,
        )
    except ImportError:
        logger.warning("xgboost not installed — skipped.")

    try:
        from lightgbm import LGBMClassifier
        candidates["lightgbm"] = LGBMClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.08,
            min_child_samples=8, random_state=random_state, verbose=-1,
        )
    except ImportError:
        logger.warning("lightgbm not installed — skipped.")

    try:
        from catboost import CatBoostClassifier
        candidates["catboost"] = CatBoostClassifier(
            iterations=150, depth=3, learning_rate=0.08,
            random_state=random_state, verbose=0,
        )
    except ImportError:
        logger.warning("catboost not installed — skipped.")

    return candidates


def _cross_val_oof_proba(estimator, X: pd.DataFrame, y: pd.Series) -> np.ndarray:
    """Out-of-fold P(high_acuity) via repeated stratified CV, averaged over repeats."""
    from sklearn.base import clone
    from sklearn.model_selection import StratifiedKFold

    n = len(X)
    accum = np.zeros(n)
    counts = np.zeros(n)

    for repeat in range(N_REPEATS):
        skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE + repeat)
        for train_idx, test_idx in skf.split(X, y):
            model = clone(estimator)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            proba = model.predict_proba(X.iloc[test_idx])[:, 1]
            accum[test_idx] += proba
            counts[test_idx] += 1

    return accum / np.maximum(counts, 1)


def choose_threshold(y_true: np.ndarray, probs: np.ndarray) -> tuple[float, dict]:
    """Lowest asymmetric cost, subject to a prevalence-relative alert ceiling."""
    base_rate = float(np.mean(y_true))
    ceiling = max(ALERT_RATE_FLOOR, min(ALERT_RATE_CEILING, base_rate * MAX_ALERT_MULTIPLE))

    curve, feasible = [], []
    for t in np.arange(0.05, 0.96, 0.02):
        pred = (probs >= t).astype(int)
        fn = int(((y_true == 1) & (pred == 0)).sum())
        fp = int(((y_true == 0) & (pred == 1)).sum())
        rate = float(pred.mean())
        cost = fn * UNDER_TRIAGE_COST + fp * OVER_TRIAGE_COST
        curve.append({"threshold": round(float(t), 2), "missed": fn, "false_alarms": fp,
                      "alert_rate": round(rate, 3), "cost": round(float(cost), 1)})
        if rate <= ceiling:
            feasible.append((cost, float(t), rate))

    if feasible:
        best_cost, best, best_rate = min(feasible)
        constraint = "binding" if best_rate > ceiling * 0.92 else "slack"
    else:
        best, best_cost, best_rate, constraint = 0.5, float("inf"), 0.0, "infeasible"

    return round(best, 2), {
        "cost_curve": curve, "chosen_cost": best_cost, "base_rate": round(base_rate, 3),
        "alert_ceiling": round(ceiling, 3), "alert_rate_at_threshold": round(best_rate, 3),
        "alert_rate_constraint": constraint,
    }


def _evaluate(y_true: np.ndarray, probs: np.ndarray) -> dict:
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    threshold, cost_info = choose_threshold(y_true, probs)
    pred = (probs >= threshold).astype(int)
    fn = int(((y_true == 1) & (pred == 0)).sum())
    fp = int(((y_true == 0) & (pred == 1)).sum())
    tp = int(((y_true == 1) & (pred == 1)).sum())
    tn = int(((y_true == 0) & (pred == 0)).sum())
    recall = tp / max(tp + fn, 1)
    precision = tp / max(tp + fp, 1)

    try:
        auc = round(float(roc_auc_score(y_true, probs)), 4)
    except ValueError:
        auc = None  # degenerate case: only one class present (e.g. majority-class baseline)

    return {
        "roc_auc": auc,
        "average_precision": round(float(average_precision_score(y_true, probs)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probs)), 4),
        "chosen_threshold": threshold,
        "recall_high_acuity": round(recall, 4),
        "precision_high_acuity": round(precision, 4),
        "true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn,
        **cost_info,
    }


def _fairness_check(labeled_df: pd.DataFrame, y: pd.Series, probs: np.ndarray, threshold: float) -> dict:
    """
    Post-hoc check across the protected attributes EXCLUDED from the
    feature set. Not a gate on training — a small demo cohort (n=207)
    will not produce statistically stable subgroup rates — but it is
    reported rather than left unchecked: excluding a variable from the
    model does not exempt the model from being audited against it.
    """
    pred = (probs >= threshold).astype(int)
    out: dict = {}

    for col in ("gender", "race"):
        if col not in labeled_df.columns:
            continue
        for value, mask in labeled_df[col].fillna("(none)").groupby(labeled_df[col].fillna("(none)")).groups.items():
            idx = labeled_df.index.get_indexer(mask)
            n = len(idx)
            if n < 5:  # too small to report a stable rate
                continue
            sub_y, sub_pred = y.to_numpy()[idx], pred[idx]
            n_pos = int((sub_y == 1).sum())
            fn = int(((sub_y == 1) & (sub_pred == 0)).sum())
            out[f"{col}_{value}"] = {
                "n": n, "flagged_rate": round(float(sub_pred.mean()), 3),
                "high_acuity_prevalence": round(float(sub_y.mean()), 3),
                "recall_high_acuity": round(1 - fn / max(n_pos, 1), 3) if n_pos else None,
            }

    return out


def train(verbose: bool = True) -> dict:
    settings = get_settings()
    X, y, feature_names = load_training_frame()
    y_arr = y.to_numpy()

    candidates = _build_candidates()
    results: dict[str, TrainedModel] = {}

    for name, estimator in candidates.items():
        if verbose:
            logger.info("Evaluating %s via %d-fold x %d-repeat CV...", name, N_SPLITS, N_REPEATS)
        oof = _cross_val_oof_proba(estimator, X, y)
        metrics = _evaluate(y_arr, oof)
        results[name] = TrainedModel(name=name, estimator=estimator, cv_probabilities=oof, metrics=metrics)
        if verbose:
            auc_str = f"{metrics['roc_auc']:.4f}" if metrics["roc_auc"] is not None else "n/a"
            logger.info(
                "  %-28s auc=%s ap=%.4f recall=%.3f precision=%.3f alerts=%.0f%%",
                name, auc_str, metrics["average_precision"],
                metrics["recall_high_acuity"], metrics["precision_high_acuity"],
                metrics["alert_rate_at_threshold"] * 100,
            )

    # Winner: highest average precision among non-baseline models with a
    # defined ROC-AUC (excludes the majority-class dummy, which cannot
    # produce a ranking and would otherwise "win" on brier score alone).
    ranked = sorted(
        (r for r in results.values() if r.name != "baseline_majority_class" and r.metrics["roc_auc"] is not None),
        key=lambda r: r.metrics["average_precision"],
        reverse=True,
    )
    if not ranked:
        raise RuntimeError("No candidate model produced a valid ranking — check the training data.")
    best = ranked[0]
    baseline = results.get("baseline_logistic_regression")

    if verbose:
        logger.info(
            "Best model: %s (average_precision=%.4f) vs logistic-regression baseline (%.4f)",
            best.name, best.metrics["average_precision"],
            baseline.metrics["average_precision"] if baseline else float("nan"),
        )

    # Refit the winner on the FULL labeled cohort for deployment — the
    # CV loop above is for honest evaluation only, never for the shipped
    # artifact, so the deployed model uses every labeled row available.
    from sklearn.base import clone
    final_model = clone(best.estimator)
    final_model.fit(X, y)

    from ml.preprocess import build_readable_frame
    fairness = _fairness_check(
        build_readable_frame().dropna(subset=[LABEL_COLUMN]),
        y, best.cv_probabilities, best.metrics["chosen_threshold"],
    )

    version = f"{best.name}-{datetime.now(timezone.utc):%Y%m%d-%H%M}"
    comparison = {
        name: {k: v for k, v in r.metrics.items() if k != "cost_curve"}
        for name, r in results.items()
    }

    report = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_labeled": int(len(X)),
        "n_features": len(feature_names),
        "prevalence_high_acuity": round(float(y.mean()), 4),
        "excluded_features": {
            "temporal_leakage": "disposition_* — recorded after the stay ends, not known at triage time",
            "protected_attributes": "race_*, gender_* — excluded from model inputs on clinical-ethics "
                                    "grounds; retained for the fairness_check below",
            "degenerate": "age_group_Unknown — constant across all rows in this data extract",
        },
        "evaluation_method": (
            f"{N_SPLITS}-fold x {N_REPEATS}-repeat stratified cross-validation, out-of-fold "
            "predictions. Metrics below are cross-validated, NOT held-out-test — the labeled "
            "cohort (207 rows) is too small for a trustworthy single split."
        ),
        "cost_model": {"under_triage_cost": UNDER_TRIAGE_COST, "over_triage_cost": OVER_TRIAGE_COST,
                       "ratio": UNDER_TRIAGE_COST / OVER_TRIAGE_COST},
        "selected_model": best.name,
        "selected_model_metrics": comparison[best.name],
        "model_comparison": comparison,
        "fairness_check": fairness,
        "known_limitations": [
            "age_group is 'Unknown' for 100% of stays — the source edstays.csv.gz has no "
            "anchor_age column in this demo extract, so the model cannot currently learn "
            "age-specific patterns even though the platform's clinical design requires them.",
            "n=207 labeled stays is small for a clinical model; cross-validated metrics have "
            "wide uncertainty and should not be read as production-grade performance.",
            "Acuity level 4 has only 2 examples and level 5 has none in this extract; the "
            "binary framing above sidesteps this but a future 5-level model would need far "
            "more data before it is trustworthy.",
        ],
    }

    _save_artifacts(final_model, feature_names, best.metrics["chosen_threshold"], report, version)
    _log_to_mlflow(report, final_model, feature_names)
    _generate_shap_summary(final_model, X, feature_names, version)

    if verbose:
        logger.info("Training complete. Artifacts saved under %s", settings.REPORTS_DIR)
    return report


def _save_artifacts(model, feature_names: list[str], threshold: float, report: dict, version: str) -> None:
    settings = get_settings()
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {"model": model, "feature_names": feature_names, "threshold": threshold, "version": version},
        settings.REPORTS_DIR / "model.joblib",
    )
    (settings.REPORTS_DIR / "metrics.json").write_text(json.dumps(report, indent=2, default=str))
    logger.info("Saved model artifact and metrics.json to %s", settings.REPORTS_DIR)


def _log_to_mlflow(report: dict, model, feature_names: list[str]) -> None:
    """Best-effort MLflow logging — a broken/unavailable tracking store must never fail training."""
    settings = get_settings()
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        with mlflow.start_run(run_name=report["version"]):
            mlflow.log_param("selected_model", report["selected_model"])
            mlflow.log_param("n_labeled", report["n_labeled"])
            mlflow.log_param("n_features", report["n_features"])
            for k, v in report["selected_model_metrics"].items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, v)
            mlflow.sklearn.log_model(model, "model")
        logger.info("Logged run to MLflow at %s", settings.MLFLOW_TRACKING_URI)
    except Exception as exc:  # noqa: BLE001 — tracking is observability, never a hard dependency
        logger.warning("MLflow logging skipped: %s", exc)


def _select_positive_class(values) -> np.ndarray:
    """
    Normalize SHAP output to a 2D (n_samples, n_features) array for the
    positive (high-acuity) class.

    Different SHAP versions/explainers disagree on shape: some return a
    list of two (n_samples, n_features) arrays (one per class), others
    return one (n_samples, n_features, n_classes) array. Both are
    handled explicitly here rather than assumed.
    """
    arr = np.asarray(values[1] if isinstance(values, list) else values)
    if arr.ndim == 3:
        return arr[:, :, 1]  # (n_samples, n_features, n_classes) -> positive class
    return arr


def _generate_shap_summary(model, X: pd.DataFrame, feature_names: list[str], version: str) -> None:
    """
    Mean absolute SHAP value per feature, saved as JSON — the same shape
    of explanation surfaced later via `/api/v1/model/predict`. Falls back
    to permutation importance if the winning model has no SHAP-compatible
    explainer (e.g. the logistic-regression baseline).
    """
    settings = get_settings()
    try:
        import shap
        from sklearn.pipeline import Pipeline

        if isinstance(model, Pipeline):
            # Wrapping predict_proba in a plain function avoids a known
            # shap/sklearn incompatibility where KernelExplainer tries to
            # set attributes directly on a Pipeline object.
            def _predict_proba(data):
                return model.predict_proba(pd.DataFrame(data, columns=feature_names))

            background = shap.sample(X, min(50, len(X)), random_state=RANDOM_STATE)
            explainer = shap.KernelExplainer(_predict_proba, background)
            sample = X.sample(min(60, len(X)), random_state=RANDOM_STATE)
            values = explainer.shap_values(sample, silent=True)
            arr = _select_positive_class(values)
        else:
            explainer = shap.TreeExplainer(model)
            values = explainer.shap_values(X)
            arr = _select_positive_class(values)

        mean_abs = np.abs(np.asarray(arr)).mean(axis=0)
        ranking = sorted(zip(feature_names, mean_abs.tolist()), key=lambda t: -t[1])
        payload = {"version": version, "method": "shap", "feature_importance": ranking[:20]}
    except Exception as exc:  # noqa: BLE001
        logger.warning("SHAP explanation failed (%s) — falling back to permutation importance.", exc)
        from sklearn.inspection import permutation_importance

        r = permutation_importance(model, X, model.predict(X), n_repeats=10, random_state=RANDOM_STATE)
        ranking = sorted(zip(feature_names, r.importances_mean.tolist()), key=lambda t: -t[1])
        payload = {"version": version, "method": "permutation_importance", "feature_importance": ranking[:20]}

    (settings.REPORTS_DIR / "feature_importance.json").write_text(json.dumps(payload, indent=2))
    logger.info("Saved feature importance (%s) to reports/feature_importance.json", payload["method"])


if __name__ == "__main__":
    result = train()
    print("\n=== PatientTriage.ai — Model Training Summary ===")
    print(f"Selected model : {result['selected_model']}")
    print(f"Labeled stays  : {result['n_labeled']}  (prevalence high-acuity: {result['prevalence_high_acuity']:.1%})")
    print(f"ROC-AUC        : {result['selected_model_metrics']['roc_auc']}")
    print(f"Recall (high)  : {result['selected_model_metrics']['recall_high_acuity']}")
    print(f"Precision(high): {result['selected_model_metrics']['precision_high_acuity']}")
    print(f"Alert rate     : {result['selected_model_metrics']['alert_rate_at_threshold']:.1%}")
    print("\nModel comparison (average precision, cross-validated):")
    for name, m in sorted(result["model_comparison"].items(), key=lambda kv: -(kv[1]["average_precision"] or 0)):
        print(f"  {name:28s} ap={m['average_precision']:.4f}")
    print(f"\nFull report: backend/reports/metrics.json")
