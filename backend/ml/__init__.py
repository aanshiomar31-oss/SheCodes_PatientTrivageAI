"""
ml package
============

PatientTriage.ai — Hybrid Intelligence Layer
--------------------------------------------------
    Patient Data -> Rule Engine -> Ensemble ML -> Uncertainty -> SHAP -> Recommendation

Modules
    rule_engine.py   Deterministic red-flag detection; always runs first, sets a floor
    model_utils.py   Shared feature building + model I/O (single train/serve contract)
    train_model.py   Stacking ensemble training (XGBoost/LightGBM/CatBoost/HistGB + LR meta)
    uncertainty.py   Confidence = calibrated probability + ensemble agreement + data completeness
    explain.py       SHAP visualizations + evaluation report, saved to backend/reports/
    predict.py       predict(patient_dict) — the single public entry point

Governing rule: "The AI recommends. The nurse decides." Nothing in this
package writes to the triage queue or changes patient priority
autonomously — see `app/api/routes/triage.py` for how a prediction is
surfaced, stored, and made overridable.

Note on existing sibling modules
-------------------------------------
`data_loader.py`, `features.py`, and `preprocess.py` already existed in
this package (the MIMIC-IV-ED data pipeline) before this hybrid
intelligence layer was added, and are unrelated to it — they feed
`triage_stays` via `load_triage_stays.py`, not `predict()`.
"""
