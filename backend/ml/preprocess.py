"""
ml/preprocess.py
==================

PatientTriage.ai — Clinical Preprocessing Pipeline
------------------------------------------------------
Orchestrates the full data engineering flow:

    raw CSVs (ml.data_loader) -> merge edstays + triage -> engineer
    clinical features (ml.features) -> impute / encode / scale (sklearn)
    -> backend/data/processed_triage.csv
                                -> backend/reports/data_quality_report.html

`vitalsign` is intentionally kept SEPARATE from the merged triage table.
It is a longitudinal (multiple-rows-per-stay) table reserved for future
real-time deterioration monitoring; merging it here would either explode
row counts or silently discard repeated measurements.

Clinical safety principles enforced in this module
-----------------------------------------------------
* Zero-history patients (no documented chief complaint, no prior
  medication reconciliation, etc.) are PRESERVED, never dropped — they
  are flagged (`missing_history_flag`) so downstream review knows to
  treat them with more, not less, caution.
* Missing values are never silently imputed to a "normal"/reassuring
  value for clinically meaningful fields — imputation choices are
  explicit and logged.
* Paths and logging reuse the existing app architecture
  (`app.core.config`, `app.core.logging_config`) rather than
  reinventing configuration.

"The AI recommends. The nurse decides."
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from ml.data_loader import load_all_tables
from ml.features import engineer_all_features

configure_logging()
logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Column groupings used to build the sklearn preprocessing pipeline.
# --------------------------------------------------------------------------- #
ID_COLUMNS = ["subject_id", "hadm_id", "stay_id"]
LABEL_COLUMN = "acuity"
TEXT_COLUMNS = ["chiefcomplaint"]
# Binary flags engineered in features.py are already 0/1 (or <NA>) —
# scaling them would make them harder to interpret for clinical review,
# so they pass through untouched rather than going through StandardScaler.
BINARY_FLAG_COLUMNS = ["missing_history_flag", "night_shift_flag", "weekend_flag"]

CATEGORICAL_COLUMNS = ["gender", "race", "arrival_transport", "disposition", "age_group"]

NUMERICAL_COLUMNS = [
    "temperature",
    "heartrate",
    "resprate",
    "o2sat",
    "sbp",
    "dbp",
    "pain",
    "shock_index",
    "pulse_pressure",
    "mean_arterial_pressure",
    "abnormal_vitals_count",
    "vitals_missing_count",
    "arrival_hour",
]


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
def merge_core_tables(edstays: pd.DataFrame, triage: pd.DataFrame) -> pd.DataFrame:
    """
    Merge `edstays` and `triage` on `stay_id` into one row-per-ED-stay table.

    Uses a LEFT join anchored on `edstays` (not an inner join): an ED stay
    with no matching triage record is still a real patient encounter and
    must be preserved — dropping it would silently remove zero-history /
    incompletely-triaged patients from the dataset, which is exactly the
    population most in need of review, not exclusion.

    Parameters
    ----------
    edstays : pd.DataFrame
        ED stay-level table (arrival/discharge time, demographics, disposition).
    triage : pd.DataFrame
        Triage-time vitals and acuity, at most one row per `stay_id`.

    Returns
    -------
    pd.DataFrame
        Left-joined table on `stay_id`, same row count as `edstays`.

    Raises
    ------
    KeyError
        If `stay_id` is missing from either input table.
    """
    if "stay_id" not in edstays.columns:
        raise KeyError("'stay_id' not found in edstays — cannot merge.")
    if "stay_id" not in triage.columns:
        raise KeyError("'stay_id' not found in triage — cannot merge.")

    n_edstays = len(edstays)

    dup_triage_stays = triage["stay_id"].duplicated().sum()
    if dup_triage_stays:
        logger.warning(
            "triage has %d duplicate stay_id rows — merge will fan out those stays. "
            "Consider deduplicating triage upstream if this is unexpected.",
            dup_triage_stays,
        )

    merged = edstays.merge(
        triage,
        on="stay_id",
        how="left",
        suffixes=("_edstays", "_triage"),
    )

    n_unmatched = merged[LABEL_COLUMN].isna().sum() if LABEL_COLUMN in merged.columns else None
    logger.info(
        "Merged edstays (%d rows) + triage (%d rows) -> %d rows on stay_id (left join, zero-history stays preserved).",
        n_edstays,
        len(triage),
        len(merged),
    )
    if n_unmatched:
        logger.warning(
            "%d ED stays have no matching triage record (missing '%s') — "
            "PRESERVED in the dataset, not dropped, and should be treated "
            "as high-uncertainty by any downstream model.",
            int(n_unmatched),
            LABEL_COLUMN,
        )

    # De-duplicate subject_id columns produced by overlapping column names.
    if "subject_id_edstays" in merged.columns and "subject_id_triage" in merged.columns:
        mismatches = (
            merged["subject_id_edstays"] != merged["subject_id_triage"]
        ) & merged["subject_id_triage"].notna()
        if mismatches.sum() > 0:
            logger.warning(
                "%d rows have mismatched subject_id between edstays and triage "
                "after merge on stay_id — keeping edstays' subject_id.",
                int(mismatches.sum()),
            )
        merged["subject_id"] = merged["subject_id_edstays"]
        merged = merged.drop(columns=["subject_id_edstays", "subject_id_triage"])

    assert len(merged) == n_edstays, "merge_core_tables must preserve every edstays row (zero-history patients included)."
    return merged


# --------------------------------------------------------------------------- #
# Numeric coercion (pre-pipeline safety net for real-world data entry noise)
# --------------------------------------------------------------------------- #
def coerce_numeric_columns(df: pd.DataFrame, numeric_columns: Optional[list[str]] = None) -> pd.DataFrame:
    """
    Coerce columns that SHOULD be numeric vitals into numeric dtype,
    turning any non-numeric entry into NaN rather than crashing.

    Real-world ED triage documentation is not always a clean number —
    e.g. the `pain` field in the MIMIC-IV-ED dataset contains free-text
    entries such as "Critical", "unable", "UA" (unable to answer), or
    "ett" (patient intubated, cannot self-report) alongside numeric 0-10
    scores. Silently `float()`-ing this column would crash the pipeline;
    silently coercing it to 0 would fabricate a reassuring "no pain"
    value for a patient who was, e.g., too critical to answer. Turning
    it into NaN is the only option consistent with the clinical safety
    principle that missing data increases uncertainty rather than being
    smoothed away — the resulting NaN is then median-imputed (visibly,
    via the sklearn pipeline) like any other missing vital.

    Parameters
    ----------
    df : pd.DataFrame
        Merged clinical table.
    numeric_columns : Optional[list[str]]
        Columns to coerce. Defaults to `NUMERICAL_COLUMNS`.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with each column in `numeric_columns` cast to
        float64 via `pd.to_numeric(errors="coerce")`. Same row count.
    """
    df = df.copy()
    numeric_columns = numeric_columns or NUMERICAL_COLUMNS

    for col in numeric_columns:
        if col not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        original = df[col]
        coerced = pd.to_numeric(original, errors="coerce")
        newly_null_mask = coerced.isna() & original.notna()
        n_newly_null = int(newly_null_mask.sum())

        if n_newly_null:
            offending_values = original[newly_null_mask].astype(str).value_counts().head(10).to_dict()
            logger.warning(
                "Column '%s' contained %d non-numeric value(s) — coerced to NaN "
                "(never guessed/imputed to a specific number here; treated as "
                "missing, not zero). Examples: %s",
                col,
                n_newly_null,
                offending_values,
            )

        df[col] = coerced

    return df


# --------------------------------------------------------------------------- #
# Missing value handling (pre-pipeline safety net)
# --------------------------------------------------------------------------- #
def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply safe, clinically-reasonable defaults before the sklearn pipeline.

    This pass NEVER drops rows — zero-history / unmatched-triage patients
    are preserved through the whole pipeline, only flagged. Numerical
    imputation for modeling is left to the sklearn `SimpleImputer` inside
    `build_preprocessing_pipeline`, so that strategy is auditable and
    reproducible at inference time via the fitted pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Merged, feature-engineered table.

    Returns
    -------
    pd.DataFrame
        Copy of `df`, SAME ROW COUNT, with text/categorical placeholders
        filled.
    """
    rows_in = len(df)
    df = df.copy()

    for col in TEXT_COLUMNS:
        if col in df.columns:
            n_missing = int(df[col].isna().sum())
            if n_missing:
                logger.info("Filling %d missing '%s' values with 'Not documented'.", n_missing, col)
            df[col] = df[col].fillna("Not documented")

    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            n_missing = int(df[col].isna().sum())
            if n_missing:
                logger.info("Filling %d missing '%s' values with 'Unknown'.", n_missing, col)
            df[col] = df[col].fillna("Unknown")

    if LABEL_COLUMN in df.columns:
        n_missing_label = int(df[LABEL_COLUMN].isna().sum())
        if n_missing_label:
            logger.warning(
                "%d rows have missing '%s' (label) — these are zero-history/"
                "untriaged stays. KEPT in the processed dataset; the "
                "modeling milestone must explicitly decide how to handle "
                "them (e.g. exclude from supervised training, but still "
                "score/flag for nurse review).",
                n_missing_label,
                LABEL_COLUMN,
            )

    assert len(df) == rows_in, "handle_missing_values must never drop rows."
    return df


# --------------------------------------------------------------------------- #
# sklearn preprocessing pipeline
# --------------------------------------------------------------------------- #
def build_preprocessing_pipeline(
    categorical_columns: Optional[list[str]] = None,
    numerical_columns: Optional[list[str]] = None,
) -> ColumnTransformer:
    """
    Build a reusable sklearn `ColumnTransformer` for triage features.

    * Numerical columns: median-impute, then standard-scale (zero mean,
      unit variance) — robust to the differing units/ranges of vitals
      (e.g. temperature ~98 vs shock_index ~0.7).
    * Categorical columns: most-frequent-impute, then one-hot encode
      (unknown categories at inference time are safely ignored rather
      than raising, which matters for a live clinical system).

    Parameters
    ----------
    categorical_columns : Optional[list[str]]
        Defaults to module-level `CATEGORICAL_COLUMNS`.
    numerical_columns : Optional[list[str]]
        Defaults to module-level `NUMERICAL_COLUMNS`.

    Returns
    -------
    ColumnTransformer
        Unfitted transformer. Call `.fit_transform(df)` once, then reuse
        the FITTED transformer (e.g. via joblib) at inference time so
        train/serve preprocessing stays consistent.
    """
    categorical_columns = categorical_columns or CATEGORICAL_COLUMNS
    numerical_columns = numerical_columns or NUMERICAL_COLUMNS

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numerical", numeric_pipeline, numerical_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    logger.info(
        "Built ColumnTransformer: %d numerical cols, %d categorical cols.",
        len(numerical_columns),
        len(categorical_columns),
    )
    return preprocessor


def apply_preprocessing_pipeline(
    df: pd.DataFrame,
    categorical_columns: Optional[list[str]] = None,
    numerical_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Fit-transform `df` with a `ColumnTransformer` and reattach passthrough
    columns (IDs, label, text, binary flags) untouched.

    Parameters
    ----------
    df : pd.DataFrame
        Merged, feature-engineered, missing-value-handled table.
    categorical_columns, numerical_columns : Optional[list[str]]
        Overrides for which columns get encoded/scaled.

    Returns
    -------
    pd.DataFrame
        Final processed table: passthrough columns + scaled numerical
        columns + one-hot encoded categorical columns. Same row count as
        input — no rows dropped by preprocessing.
    """
    rows_in = len(df)
    categorical_columns = categorical_columns or CATEGORICAL_COLUMNS
    numerical_columns = numerical_columns or NUMERICAL_COLUMNS

    available_numerical = [c for c in numerical_columns if c in df.columns]
    available_categorical = [c for c in categorical_columns if c in df.columns]

    missing_numerical = set(numerical_columns) - set(available_numerical)
    missing_categorical = set(categorical_columns) - set(available_categorical)
    if missing_numerical:
        logger.warning("Numerical columns not found in frame, skipped: %s", missing_numerical)
    if missing_categorical:
        logger.warning("Categorical columns not found in frame, skipped: %s", missing_categorical)

    # Rebuild the transformer against only the columns actually present,
    # so a partially-available schema never crashes the pipeline.
    preprocessor = build_preprocessing_pipeline(
        categorical_columns=available_categorical,
        numerical_columns=available_numerical,
    )

    transformed_array = preprocessor.fit_transform(df)
    feature_names = preprocessor.get_feature_names_out()
    transformed_df = pd.DataFrame(transformed_array, columns=feature_names, index=df.index)

    passthrough_columns = [
        c for c in ID_COLUMNS + [LABEL_COLUMN] + TEXT_COLUMNS + BINARY_FLAG_COLUMNS if c in df.columns
    ]
    passthrough_df = df[passthrough_columns].reset_index(drop=True)
    transformed_df = transformed_df.reset_index(drop=True)

    final_df = pd.concat([passthrough_df, transformed_df], axis=1)

    assert len(final_df) == rows_in, "apply_preprocessing_pipeline must never drop rows."
    logger.info("Final processed dataset shape: %s", final_df.shape)
    return final_df


# --------------------------------------------------------------------------- #
# Data quality report (self-contained HTML, no extra dependencies)
# --------------------------------------------------------------------------- #
def _css_bar_rows(labels: list[str], counts: list[int], max_bar_px: int = 320) -> str:
    """Render a list of (label, count) as CSS horizontal bar rows."""
    max_count = max(counts) if counts else 0
    rows = []
    for label, count in zip(labels, counts):
        width = int((count / max_count) * max_bar_px) if max_count else 0
        rows.append(
            f'<div class="bar-row">'
            f'<span class="bar-label">{html.escape(str(label))}</span>'
            f'<span class="bar" style="width:{width}px;"></span>'
            f'<span class="bar-count">{count}</span>'
            f"</div>"
        )
    return "\n".join(rows)


def _missing_value_summary_html(df: pd.DataFrame) -> str:
    """Build the missing-value summary table (column, dtype, missing count/%)."""
    n_rows = len(df)
    summary = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(df[c].dtype) for c in df.columns],
            "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        }
    )
    summary["missing_pct"] = (summary["missing_count"] / n_rows * 100).round(2) if n_rows else 0.0
    summary = summary.sort_values("missing_count", ascending=False)

    rows_html = "\n".join(
        f"<tr><td>{html.escape(r.column)}</td><td>{html.escape(r.dtype)}</td>"
        f"<td>{r.missing_count}</td><td>{r.missing_pct}%</td></tr>"
        for r in summary.itertuples(index=False)
    )
    return (
        "<table><thead><tr><th>Column</th><th>Type</th>"
        "<th>Missing Count</th><th>Missing %</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )


def _duplicate_check_html(df: pd.DataFrame) -> str:
    """Build the duplicate-record check section."""
    n_full_dupes = int(df.duplicated().sum())
    n_stay_dupes = int(df["stay_id"].duplicated().sum()) if "stay_id" in df.columns else None
    n_subject_dupes = int(df["subject_id"].duplicated().sum()) if "subject_id" in df.columns else None

    items = [f"<li>Fully duplicated rows: <strong>{n_full_dupes}</strong></li>"]
    if n_stay_dupes is not None:
        items.append(f"<li>Duplicate <code>stay_id</code> values: <strong>{n_stay_dupes}</strong></li>")
    if n_subject_dupes is not None:
        items.append(
            f"<li>Duplicate <code>subject_id</code> values (expected — patients can have "
            f"multiple ED stays): <strong>{n_subject_dupes}</strong></li>"
        )
    return "<ul>" + "\n".join(items) + "</ul>"


def _age_distribution_html(df: pd.DataFrame, age_col: str = "anchor_age") -> str:
    """Build the age-distribution section, bucketed into 10-year bins."""
    if age_col not in df.columns:
        return f"<p><em>Column '{html.escape(age_col)}' not available — age distribution skipped.</em></p>"

    ages = df[age_col].dropna()
    if ages.empty:
        return "<p><em>No non-missing age values available.</em></p>"

    bins = list(range(0, 100, 10)) + [np.inf]
    bin_labels = [f"{b}-{b + 9}" for b in range(0, 90, 10)] + ["90+"]
    bucketed = pd.cut(ages, bins=bins, labels=bin_labels, right=False)
    counts = bucketed.value_counts().reindex(bin_labels, fill_value=0)

    return (
        f"<p>n = {len(ages)} patients with known age "
        f"(mean={ages.mean():.1f}, median={ages.median():.1f})</p>"
        f'<div class="bar-chart">{_css_bar_rows(counts.index.tolist(), counts.values.tolist())}</div>'
    )


def _acuity_distribution_html(df: pd.DataFrame, acuity_col: str = LABEL_COLUMN) -> str:
    """Build the acuity-distribution section."""
    if acuity_col not in df.columns:
        return f"<p><em>Column '{html.escape(acuity_col)}' not available — acuity distribution skipped.</em></p>"

    acuity = df[acuity_col]
    n_missing = int(acuity.isna().sum())
    counts = acuity.dropna().value_counts().sort_index()

    labels = [f"Acuity {int(v)}" for v in counts.index]
    body = _css_bar_rows(labels, counts.values.tolist())
    missing_note = (
        f'<p class="warning">{n_missing} stays have no acuity recorded '
        f"(zero-history / untriaged — preserved in the dataset, excluded from this chart).</p>"
        if n_missing
        else ""
    )
    return f'<div class="bar-chart">{body}</div>{missing_note}'


def _arrival_hour_histogram_html(df: pd.DataFrame, hour_col: str = "arrival_hour") -> str:
    """Build the arrival-hour histogram section (0-23)."""
    if hour_col not in df.columns:
        return f"<p><em>Column '{html.escape(hour_col)}' not available — arrival-hour histogram skipped.</em></p>"

    hours = df[hour_col].dropna().astype(int)
    if hours.empty:
        return "<p><em>No parseable arrival timestamps available.</em></p>"

    counts = hours.value_counts().reindex(range(24), fill_value=0)
    labels = [f"{h:02d}:00" for h in range(24)]
    return f'<div class="bar-chart hourly">{_css_bar_rows(labels, counts.values.tolist())}</div>'


def generate_data_quality_report(df: pd.DataFrame, output_path: Path) -> None:
    """
    Generate a self-contained HTML data-quality report (no external
    plotting library required — charts are rendered as CSS bars so the
    report has zero runtime dependencies beyond a web browser).

    Sections
    --------
    * Missing value summary (per column, count + percentage)
    * Duplicate check (full-row, stay_id, subject_id)
    * Age distribution (10-year buckets)
    * Acuity distribution (triage acuity value counts)
    * Arrival-hour histogram (0-23)

    Parameters
    ----------
    df : pd.DataFrame
        The merged, feature-engineered (pre-scaling) clinical dataset —
        i.e. the frame right after `handle_missing_values`, BEFORE the
        sklearn ColumnTransformer, so distributions are in clinically
        readable units rather than standardized/one-hot form.
    output_path : Path
        Destination `.html` file. Parent directories are created if needed.
    """
    logger.info("Generating data quality report for frame with shape=%s", df.shape)

    style = """
    <style>
        body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
               background: #f8fafc; color: #0f172a; margin: 0; padding: 2rem; }
        .container { max-width: 960px; margin: 0 auto; }
        h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
        .subtitle { color: #64748b; margin-top: 0; margin-bottom: 2rem; }
        .banner { background: #eff6ff; color: #1e40af; padding: 0.75rem 1rem;
                   border-radius: 8px; font-weight: 600; margin-bottom: 2rem; }
        section { background: white; border: 1px solid #e2e8f0; border-radius: 12px;
                  padding: 1.5rem; margin-bottom: 1.5rem; }
        h2 { font-size: 1.1rem; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #f1f5f9; }
        th { color: #64748b; font-weight: 600; }
        code { background: #f1f5f9; padding: 0.1rem 0.35rem; border-radius: 4px; }
        .bar-chart { display: flex; flex-direction: column; gap: 4px; }
        .bar-chart.hourly { font-size: 0.75rem; }
        .bar-row { display: flex; align-items: center; gap: 8px; }
        .bar-label { width: 80px; flex-shrink: 0; color: #475569; font-size: 0.8rem; }
        .bar { background: #2563eb; height: 14px; border-radius: 3px; min-width: 2px; }
        .bar-count { color: #64748b; font-size: 0.8rem; }
        .warning { color: #b45309; font-size: 0.85rem; }
        footer { color: #94a3b8; font-size: 0.75rem; text-align: center; margin-top: 2rem; }
    </style>
    """

    generated_at = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")

    report_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PatientTriage.ai — Data Quality Report</title>
{style}
</head>
<body>
<div class="container">
    <h1>PatientTriage.ai — Data Quality Report</h1>
    <p class="subtitle">Generated {generated_at} · {len(df)} rows · {len(df.columns)} columns</p>
    <div class="banner">The AI recommends. The nurse decides. This report describes the
        merged edstays + triage dataset prior to model training.</div>

    <section>
        <h2>Missing Value Summary</h2>
        {_missing_value_summary_html(df)}
    </section>

    <section>
        <h2>Duplicate Check</h2>
        {_duplicate_check_html(df)}
    </section>

    <section>
        <h2>Age Distribution</h2>
        {_age_distribution_html(df)}
    </section>

    <section>
        <h2>Acuity Distribution</h2>
        {_acuity_distribution_html(df)}
    </section>

    <section>
        <h2>Arrival Hour Histogram</h2>
        {_arrival_hour_histogram_html(df)}
    </section>

    <footer>PatientTriage.ai — Milestone 2 data pipeline · backend/ml/preprocess.py</footer>
</div>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_html, encoding="utf-8")
    logger.info("Saved data quality report to %s", output_path.resolve())


# --------------------------------------------------------------------------- #
# Readable frame for database loading (kept SEPARATE from the scaled/
# one-hot ML export below — see app/models/triage_stay.py for why).
# --------------------------------------------------------------------------- #
READABLE_COLUMNS = [
    "stay_id", "subject_id", "hadm_id",
    "gender", "race", "arrival_transport", "disposition", "age_group",
    "chiefcomplaint",
    "temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp", "pain",
    "shock_index", "pulse_pressure", "mean_arterial_pressure",
    "abnormal_vitals_count", "vitals_missing_count", "missing_history_flag",
    "arrival_hour", "night_shift_flag", "weekend_flag",
    "acuity",
]


def build_readable_frame(
    data_dir: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Run the pipeline through feature engineering and missing-value
    handling, but STOP before the sklearn `ColumnTransformer` step, so
    the result is in original clinical units — this is what
    `app/models/triage_stay.py::TriageStay` is loaded from, and what the
    dashboard reads. `run_preprocessing()` continues past this point to
    produce the scaled/encoded ML training artifact; the two paths share
    every step up to here rather than duplicating logic.

    Parameters
    ----------
    data_dir : Optional[str | Path]
        Defaults to `settings.DATA_DIR`, same as `run_preprocessing`.

    Returns
    -------
    pd.DataFrame
        One row per ED stay, `READABLE_COLUMNS` only, original units.

    Raises
    ------
    RuntimeError
        If `edstays` or `triage` failed to load.
    """
    settings = get_settings()
    data_dir = Path(data_dir) if data_dir is not None else settings.DATA_DIR

    tables, report = load_all_tables(data_dir)
    if "edstays" not in tables or "triage" not in tables:
        raise RuntimeError(
            "build_readable_frame requires both 'edstays' and 'triage' to load. "
            f"Load report: {report.summary()}"
        )

    merged = merge_core_tables(tables["edstays"], tables["triage"])
    merged = coerce_numeric_columns(merged)
    merged = engineer_all_features(merged)
    merged = handle_missing_values(merged)

    available = [c for c in READABLE_COLUMNS if c in merged.columns]
    missing = set(READABLE_COLUMNS) - set(available)
    if missing:
        logger.warning("build_readable_frame: expected columns not present, skipped: %s", missing)

    return merged[available].rename(columns={"chiefcomplaint": "chief_complaint"})


# --------------------------------------------------------------------------- #
# End-to-end orchestration
# --------------------------------------------------------------------------- #
def run_preprocessing(
    data_dir: Optional[str | Path] = None,
    output_csv_path: Optional[str | Path] = None,
    report_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Run the full PatientTriage.ai preprocessing pipeline end-to-end.

    Steps
    -----
    1. Load raw tables (`ml.data_loader.load_all_tables`).
    2. Merge `edstays` + `triage` on `stay_id`, LEFT join so zero-history
       / untriaged stays are preserved (`vitalsign` stays separate).
    3. Coerce vitals columns to numeric, turning real-world free-text
       noise (e.g. `pain="Critical"`) into NaN rather than crashing.
    4. Engineer clinical features (`ml.features.engineer_all_features`).
    5. Apply safe missing-value defaults for text/categorical columns.
    6. Generate `data_quality_report.html` from the clinically-readable
       (pre-scaling) frame.
    7. Impute + scale numerical columns, impute + one-hot encode
       categorical columns via a fitted sklearn `ColumnTransformer`.
    8. Save the result to `output_csv_path`.

    Parameters
    ----------
    data_dir : Optional[str | Path]
        Directory containing the raw `.csv.gz` files. Defaults to the
        app's configured `settings.DATA_DIR`.
    output_csv_path : Optional[str | Path]
        Destination for the processed CSV. Defaults to
        `settings.DATA_DIR / "processed_triage.csv"`.
    report_path : Optional[str | Path]
        Destination for the HTML data-quality report. Defaults to
        `settings.REPORTS_DIR / "data_quality_report.html"`.

    Returns
    -------
    pd.DataFrame
        The final processed DataFrame (same content written to disk).

    Raises
    ------
    RuntimeError
        If `edstays` or `triage` failed to load — these are the two
        tables this pipeline cannot proceed without.
    """
    settings = get_settings()
    data_dir = Path(data_dir) if data_dir is not None else settings.DATA_DIR
    output_csv_path = Path(output_csv_path) if output_csv_path is not None else settings.DATA_DIR / "processed_triage.csv"
    report_path = Path(report_path) if report_path is not None else settings.REPORTS_DIR / "data_quality_report.html"

    logger.info("=== PatientTriage.ai clinical data pipeline starting ===")
    tables, report = load_all_tables(data_dir)

    if "edstays" not in tables or "triage" not in tables:
        logger.error(
            "Cannot proceed: 'edstays' and/or 'triage' failed to load. Load report:\n%s",
            report.summary(),
        )
        raise RuntimeError(
            "Preprocessing requires both 'edstays' and 'triage' to load successfully. "
            f"Load report: {report.summary()}"
        )

    if "vitalsign" in tables:
        logger.info(
            "'vitalsign' loaded with shape=%s and is being kept SEPARATE "
            "(reserved for future real-time deterioration monitoring, not "
            "merged into the triage snapshot).",
            tables["vitalsign"].shape,
        )
    else:
        logger.warning("'vitalsign' table not available — deterioration monitoring features unavailable.")

    merged = merge_core_tables(tables["edstays"], tables["triage"])
    merged = coerce_numeric_columns(merged)
    merged = engineer_all_features(merged)
    merged = handle_missing_values(merged)

    generate_data_quality_report(merged, report_path)

    final_df = apply_preprocessing_pipeline(merged)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_csv_path, index=False)
    logger.info("Saved processed dataset to %s (shape=%s).", output_csv_path.resolve(), final_df.shape)

    logger.info("=== PatientTriage.ai clinical data pipeline complete ===")
    return final_df


# --------------------------------------------------------------------------- #
# Manual run
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    run_preprocessing()
