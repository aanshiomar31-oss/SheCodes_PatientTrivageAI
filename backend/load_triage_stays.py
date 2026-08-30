"""
load_triage_stays.py
=======================

PatientTriage.ai — Load Triage Stays into the Database
-----------------------------------------------------------
Populates `triage_stays` (see `app/models/triage_stay.py`) from the raw
MIMIC-IV-ED demo CSVs via `ml.preprocess.build_readable_frame()` — the
same merge/feature-engineering pipeline that produces
`data/processed_triage.csv`, stopped before the scaling/one-hot step so
what lands in the database is clinically readable.

Idempotent: safe to re-run. Existing rows are upserted by `stay_id`
rather than duplicated, so this can be re-run after a data refresh
without first truncating the table.

Run:
    cd backend
    python -m alembic upgrade head   # ensure the table exists
    python load_triage_stays.py
"""

from __future__ import annotations

import math

import pandas as pd

from app.core.database import SessionLocal, Base, engine
from app.core.logging_config import configure_logging, get_logger
from app.models import TriageStay
from ml.preprocess import build_readable_frame

configure_logging()
logger = get_logger(__name__)


def _clean(value):
    """NaN -> None. Everything else passes through unchanged."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    return value


def _row_to_kwargs(row: pd.Series) -> dict:
    return {
        "stay_id": int(row["stay_id"]),
        "subject_id": _clean(row.get("subject_id")) and int(row["subject_id"]),
        "hadm_id": _clean(row.get("hadm_id")) and int(row["hadm_id"]),
        "gender": _clean(row.get("gender")),
        "race": _clean(row.get("race")),
        "arrival_transport": _clean(row.get("arrival_transport")),
        "disposition": _clean(row.get("disposition")),
        "age_group": _clean(row.get("age_group")) or "Unknown",
        "chief_complaint": _clean(row.get("chief_complaint")),
        "temperature": _clean(row.get("temperature")),
        "heart_rate": _clean(row.get("heartrate")),
        "resp_rate": _clean(row.get("resprate")),
        "o2_sat": _clean(row.get("o2sat")),
        "sbp": _clean(row.get("sbp")),
        "dbp": _clean(row.get("dbp")),
        "pain": _clean(row.get("pain")),
        "shock_index": _clean(row.get("shock_index")),
        "pulse_pressure": _clean(row.get("pulse_pressure")),
        "mean_arterial_pressure": _clean(row.get("mean_arterial_pressure")),
        "abnormal_vitals_count": int(_clean(row.get("abnormal_vitals_count")) or 0),
        "vitals_missing_count": int(_clean(row.get("vitals_missing_count")) or 0),
        "missing_history_flag": bool(_clean(row.get("missing_history_flag")) or False),
        "arrival_hour": _clean(row.get("arrival_hour")) and int(row["arrival_hour"]),
        "night_shift_flag": (
            None if _clean(row.get("night_shift_flag")) is None else bool(row["night_shift_flag"])
        ),
        "weekend_flag": (
            None if _clean(row.get("weekend_flag")) is None else bool(row["weekend_flag"])
        ),
        "acuity": _clean(row.get("acuity")) and int(row["acuity"]),
    }


def load_triage_stays() -> int:
    """
    Build the readable clinical frame and upsert it into `triage_stays`.

    Returns
    -------
    int
        Number of rows written (inserted + updated).
    """
    Base.metadata.create_all(bind=engine)  # dev convenience; Alembic owns real migrations

    logger.info("Building readable clinical frame from raw MIMIC-IV-ED demo tables...")
    frame = build_readable_frame()
    logger.info("Readable frame built: shape=%s", frame.shape)

    db = SessionLocal()
    written = 0
    try:
        existing_ids = {row.stay_id for row in db.query(TriageStay.stay_id).all()}

        for _, row in frame.iterrows():
            kwargs = _row_to_kwargs(row)
            stay_id = kwargs["stay_id"]

            if stay_id in existing_ids:
                db.query(TriageStay).filter(TriageStay.stay_id == stay_id).update(kwargs)
            else:
                db.add(TriageStay(**kwargs))
            written += 1

        db.commit()
        logger.info("Loaded %d triage stays into the database.", written)
    except Exception:
        db.rollback()
        logger.exception("Failed to load triage stays — transaction rolled back.")
        raise
    finally:
        db.close()

    return written


if __name__ == "__main__":
    n = load_triage_stays()
    print(f"\nLoaded {n} triage stays into triage_stays.")
