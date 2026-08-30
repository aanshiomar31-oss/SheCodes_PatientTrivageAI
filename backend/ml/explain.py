"""
ml/explain.py
================

PatientTriage.ai — Explainable AI + Evaluation Report
-------------------------------------------------------------
Generates the SHAP explainability artifacts and evaluation
visualizations required alongside the trained ensemble, saved to
`backend/reports/`. Run after `train_model.py`.

Run:
    cd backend
    python -m ml.explain
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")  # headless — this module never opens a display window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (ConfusionMatrixDisplay, PrecisionRecallDisplay,
                             RocCurveDisplay, confusion_matrix)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import label_binarize

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from ml.model_utils import ModelArtifact, load_artifact, load_labeled_stays

configure_logging()
logger = get_logger(__name__)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

PRIORITY_COLORS = {1: "#dc2626", 2: "#ea580c", 3: "#ca8a04", 4: "#16a34a", 5: "#2563eb"}


def generate_shap_report(artifact: ModelArtifact, X: pd.DataFrame, reports_dir) -> dict:
    """
    SHAP summary, waterfall (single representative case per class), and
    global feature-importance bar chart. Uses the HistGradientBoosting
    base learner as the SHAP subject — it is the one base model with a
    fast, exact TreeExplainer path; the calibrated stack's predictions
    are what get served, but SHAP explains the physiological reasoning
    that feeds it, which is what a clinician reviewing a recommendation
    actually wants to see.
    """
    model = artifact.base_models.get("hist_gradient_boosting")
    if model is None:
        logger.warning("No hist_gradient_boosting base model in artifact — skipping SHAP report.")
        return {"generated": False}

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # shap_values shape: (n_samples, n_features, n_classes) for multiclass HGB in recent SHAP versions.
    values = np.asarray(shap_values)
    multiclass = values.ndim == 3

    # --- Summary plot (mean |SHAP| across classes if multiclass) -----------
    plt.figure(figsize=(9, 7))
    if multiclass:
        mean_abs_per_class = np.abs(values).mean(axis=2)  # (n_samples, n_features)
        shap.summary_plot(mean_abs_per_class, X, feature_names=artifact.feature_names, show=False, plot_size=None)
    else:
        shap.summary_plot(values, X, feature_names=artifact.feature_names, show=False, plot_size=None)
    plt.title("PatientTriage.ai — SHAP Feature Impact Summary")
    plt.tight_layout()
    plt.savefig(reports_dir / "shap_summary.png", dpi=160)
    plt.close()

    # --- Global feature importance bar chart --------------------------------
    mean_abs = np.abs(values).mean(axis=(0, 2)) if multiclass else np.abs(values).mean(axis=0)
    ranking = sorted(zip(artifact.feature_names, mean_abs.tolist()), key=lambda t: -t[1])[:15]
    plt.figure(figsize=(9, 7))
    names = [r[0] for r in ranking][::-1]
    vals = [r[1] for r in ranking][::-1]
    plt.barh(names, vals, color="#2563eb")
    plt.xlabel("Mean |SHAP value|")
    plt.title("PatientTriage.ai — Global Feature Importance")
    plt.tight_layout()
    plt.savefig(reports_dir / "feature_importance.png", dpi=160)
    plt.close()

    # --- Waterfall for one representative case per trained class -----------
    for class_idx, cls in enumerate(artifact.classes):
        # model.predict() returns REMAPPED 0..n-1 labels (see train_model.py's
        # note on why: XGBoost requires it) — compare against class_idx, not
        # the true priority value cls, or this loop silently finds nothing.
        class_rows = np.where(model.predict(X) == class_idx)[0]
        if len(class_rows) == 0:
            continue
        sample_idx = int(class_rows[0])
        try:
            base_value = (
                explainer.expected_value[class_idx] if isinstance(explainer.expected_value, (list, np.ndarray))
                else explainer.expected_value
            )
            row_values = values[sample_idx, :, class_idx] if multiclass else values[sample_idx]
            explanation = shap.Explanation(
                values=row_values, base_values=base_value,
                data=X.iloc[sample_idx].values, feature_names=artifact.feature_names,
            )
            plt.figure(figsize=(9, 7))
            shap.plots.waterfall(explanation, show=False, max_display=12)
            plt.title(f"PatientTriage.ai — Example Explanation (Priority P{cls})")
            plt.tight_layout()
            plt.savefig(reports_dir / f"shap_waterfall_p{cls}.png", dpi=160)
            plt.close()
        except Exception as exc:  # noqa: BLE001 — one failed plot must not abort the report
            logger.warning("Waterfall plot for class %s failed: %s", cls, exc)
            plt.close("all")

    (reports_dir / "feature_importance.json").write_text(
        json.dumps({"method": "shap", "version": artifact.version, "feature_importance": ranking}, indent=2)
    )
    logger.info("Saved SHAP summary, waterfall(s), and feature importance to %s", reports_dir)
    return {"generated": True, "top_features": ranking[:10]}


def generate_confidence_gauge(sample_confidence: float, reports_dir) -> None:
    """A single illustrative confidence gauge, styled to match the priority color scale."""
    fig, ax = plt.subplots(figsize=(6, 3.5), subplot_kw={"aspect": "equal"})
    theta = np.linspace(np.pi, 0, 100)
    for lo, hi, color in [(0, 0.5, "#dc2626"), (0.5, 0.75, "#ca8a04"), (0.75, 1.0, "#16a34a")]:
        seg = theta[(theta >= np.pi * (1 - hi)) & (theta <= np.pi * (1 - lo))]
        ax.plot(np.cos(seg), np.sin(seg), lw=18, color=color, solid_capstyle="butt")
    needle_angle = np.pi * (1 - sample_confidence)
    ax.plot([0, 0.85 * np.cos(needle_angle)], [0, 0.85 * np.sin(needle_angle)], color="#0f172a", lw=3)
    ax.scatter([0], [0], color="#0f172a", s=40, zorder=5)
    ax.text(0, -0.25, f"{sample_confidence:.0%} confidence", ha="center", fontsize=13, fontweight="bold")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-0.4, 1.1)
    ax.axis("off")
    plt.title("PatientTriage.ai — Confidence Gauge (illustrative)")
    plt.tight_layout()
    plt.savefig(reports_dir / "confidence_gauge.png", dpi=160)
    plt.close()


def generate_evaluation_plots(artifact: ModelArtifact, X: pd.DataFrame, y_true: pd.Series, reports_dir) -> dict:
    """Confusion matrix, ROC, precision-recall, calibration, class distribution, fold summary.

    `cross_val_predict` clones and refits `artifact.meta_learner` internally,
    which contains an XGBoost base learner requiring 0..n-1 integer labels —
    the same constraint `train_model.py::train` works around. `y_true` (true
    priority labels, e.g. 1/2/3) is remapped here identically before fitting,
    then every plot and metric below is reported back in true priority terms.
    """
    classes = artifact.classes
    label_to_index = {c: i for i, c in enumerate(classes)}
    y = y_true.map(label_to_index)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof_proba = cross_val_predict(artifact.meta_learner, X, y, cv=cv, method="predict_proba")
    oof_pred = np.array(classes)[oof_proba.argmax(axis=1)]
    y_mapped = y  # keep the 0-indexed labels for the fold-fit loop below (XGBoost requires them)

    # --- Confusion matrix ----------------------------------------------------
    cm = confusion_matrix(y_true, oof_pred, labels=classes)
    fig, ax = plt.subplots(figsize=(6, 5.5))
    ConfusionMatrixDisplay(cm, display_labels=[f"P{c}" for c in classes]).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("PatientTriage.ai — Confusion Matrix (5-fold OOF)")
    plt.tight_layout()
    plt.savefig(reports_dir / "confusion_matrix.png", dpi=160)
    plt.close()

    # --- ROC + Precision-Recall (one-vs-rest per class) ----------------------
    y_bin = label_binarize(y_true, classes=classes)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, cls in enumerate(classes):
        RocCurveDisplay.from_predictions(
            y_bin[:, i], oof_proba[:, i], name=f"P{cls}", ax=ax, color=PRIORITY_COLORS.get(cls, None),
        )
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_title("PatientTriage.ai — ROC Curves (one-vs-rest, OOF)")
    plt.tight_layout()
    plt.savefig(reports_dir / "roc_curve.png", dpi=160)
    plt.close()

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, cls in enumerate(classes):
        PrecisionRecallDisplay.from_predictions(
            y_bin[:, i], oof_proba[:, i], name=f"P{cls}", ax=ax, color=PRIORITY_COLORS.get(cls, None),
        )
    ax.set_title("PatientTriage.ai — Precision-Recall Curves (one-vs-rest, OOF)")
    plt.tight_layout()
    plt.savefig(reports_dir / "precision_recall_curve.png", dpi=160)
    plt.close()

    # --- Calibration curve (per class, one-vs-rest) --------------------------
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    calibration_error = {}
    for i, cls in enumerate(classes):
        bins = np.linspace(0, 1, 11)
        bin_ids = np.digitize(oof_proba[:, i], bins) - 1
        bin_ids = np.clip(bin_ids, 0, 9)
        obs, pred = [], []
        for b in range(10):
            mask = bin_ids == b
            if mask.sum() == 0:
                continue
            obs.append(y_bin[mask, i].mean())
            pred.append(oof_proba[mask, i].mean())
        if pred:
            ax.plot(pred, obs, marker="o", label=f"P{cls}", color=PRIORITY_COLORS.get(cls, None))
            calibration_error[f"P{cls}"] = round(float(np.mean(np.abs(np.array(obs) - np.array(pred)))), 4)
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Perfectly calibrated")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title("PatientTriage.ai — Calibration Curve (OOF)")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(reports_dir / "calibration_curve.png", dpi=160)
    plt.close()

    # --- Class distribution ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 4.5))
    counts = y_true.value_counts().sort_index()
    ax.bar([f"P{c}" for c in counts.index], counts.values,
          color=[PRIORITY_COLORS.get(c, "#64748b") for c in counts.index])
    ax.set_title("PatientTriage.ai — Class Distribution (Trained Classes)")
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(reports_dir / "class_distribution.png", dpi=160)
    plt.close()

    # --- Fold performance summary ---------------------------------------------
    from sklearn.base import clone
    from sklearn.metrics import accuracy_score, f1_score

    fold_rows = []
    for fold_i, (train_idx, test_idx) in enumerate(cv.split(X, y_mapped), start=1):
        model = clone(artifact.meta_learner)
        model.fit(X.iloc[train_idx], y_mapped.iloc[train_idx])
        pred = model.predict(X.iloc[test_idx])
        fold_rows.append({
            "fold": fold_i,
            "accuracy": round(float(accuracy_score(y_mapped.iloc[test_idx], pred)), 4),
            "macro_f1": round(float(f1_score(y_mapped.iloc[test_idx], pred, average="macro")), 4),
        })

    fig, ax = plt.subplots(figsize=(6, 4.5))
    folds = [r["fold"] for r in fold_rows]
    ax.plot(folds, [r["accuracy"] for r in fold_rows], marker="o", label="Accuracy", color="#2563eb")
    ax.plot(folds, [r["macro_f1"] for r in fold_rows], marker="s", label="Macro F1", color="#16a34a")
    ax.set_xticks(folds)
    ax.set_xlabel("Fold")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.set_title("PatientTriage.ai — Fold Performance Summary")
    plt.tight_layout()
    plt.savefig(reports_dir / "fold_performance.png", dpi=160)
    plt.close()

    return {
        "calibration_error_per_class": calibration_error,
        "mean_calibration_error": round(float(np.mean(list(calibration_error.values()))), 4) if calibration_error else None,
        "fold_performance": fold_rows,
    }


def run() -> dict:
    settings = get_settings()
    reports_dir = settings.REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    artifact = load_artifact()
    if artifact is None:
        raise RuntimeError("No trained ensemble found. Run `python -m ml.train_model` first.")

    X, y, _classes = load_labeled_stays()
    logger.info("Generating explainability + evaluation report on %d labeled stays...", len(X))

    shap_result = generate_shap_report(artifact, X, reports_dir)
    eval_result = generate_evaluation_plots(artifact, X, y, reports_dir)

    proba = artifact.meta_learner.predict_proba(X.iloc[[0]])[0]
    generate_confidence_gauge(float(proba.max()), reports_dir)

    report = {
        "version": artifact.version,
        "n_evaluated": int(len(X)),
        "shap": shap_result,
        "evaluation": eval_result,
        "artifacts_saved": [
            "shap_summary.png", "feature_importance.png", "feature_importance.json",
            "confusion_matrix.png", "roc_curve.png", "precision_recall_curve.png",
            "calibration_curve.png", "class_distribution.png", "fold_performance.png",
            "confidence_gauge.png",
        ] + [f"shap_waterfall_p{c}.png" for c in artifact.classes],
    }
    (reports_dir / "explain_report.json").write_text(json.dumps(report, indent=2, default=str))
    logger.info("Explainability + evaluation report complete. See backend/reports/")
    return report


if __name__ == "__main__":
    result = run()
    print("\n=== PatientTriage.ai — Explainability & Evaluation Report ===")
    print(f"Model version   : {result['version']}")
    print(f"Evaluated on    : {result['n_evaluated']} labeled stays")
    print(f"Calibration err : {result['evaluation']['mean_calibration_error']}")
    print("Artifacts saved to backend/reports/:")
    for name in result["artifacts_saved"]:
        print(f"  - {name}")
