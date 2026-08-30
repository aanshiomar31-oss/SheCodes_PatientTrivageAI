"""
app/ml package
=================

PatientTriage.ai — App-Facing ML Surface
------------------------------------------
Milestone 3 fills this package with `model_registry.py`: a thin,
runtime-facing wrapper that loads the artifact trained by
`backend/ml/train.py` and serves predictions to the FastAPI app.

Training itself (data loading, feature engineering, model comparison,
SHAP, MLflow logging) lives in `backend/ml/` (sibling to `app/`)
alongside the data pipeline it depends on
(`data_loader.py`/`features.py`/`preprocess.py`) — this package is
deliberately kept to the "load a trained artifact and serve it" surface
only, so the FastAPI app never imports training-time dependencies like
Optuna's search loop.
"""
