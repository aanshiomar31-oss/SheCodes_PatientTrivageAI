"""
ml/features.py
================

PatientTriage.ai — Clinical Feature Engineering
------------------------------------------------
Reusable, well-documented feature functions used by the ED triage
decision-support pipeline. Each function is pure (no side effects, no
I/O) and operates on a DataFrame that already contains raw MIMIC-IV-ED
columns (from `edstays` + `triage`, merged by `preprocess.py`).

Clinical safety principles enforced throughout this module
-----------------------------------------------------------
* Age-specific thresholds are mandatory — pediatric, adult, and
  geriatric patients are never scored against the same physiological
  ranges (see `add_age_group` and `add_abnormal_vitals_count`).
* Missing data increases uncertainty, never assumed "normal" — every
  function here leaves a value as NaN/flagged rather than silently
  imputing a benign value.
* Zero-history patients (e.g. no documented chief complaint) are
  preserved and explicitly flagged, never dropped — see
  `add_missing_history_flag`.

Clinical disclaimer: these are DECISION-SUPPORT features only. They
quantify physiological derangement and context to help prioritize nurse
review — they do not diagnose. "The AI recommends. The nurse decides."
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Clinically-defined normal ranges, by age group. Under-triage is worse
# than over-triage, so these ranges intentionally err toward flagging
# borderline values as abnormal rather than passing them through as normal.
# Sources: standard ED triage reference ranges (adult/geriatric); pediatric
# ranges vary continuously with age in reality — this table uses a single
# broad pediatric band as a conservative default. Refining pediatric ranges
# by exact age band is a follow-up clinical-validation task, not a data
# engineering one.
# --------------------------------------------------------------------------- #
NORMAL_RANGES_BY_AGE_GROUP: dict[str, dict[str, tuple[float, float]]] = {
    "Pediatric": {
        "heartrate": (70, 140),
        "resprate": (16, 30),
        "sbp": (70, 120),
        "dbp": (40, 80),
        "o2sat": (95, 100),
        "temperature": (97.0, 100.4),
    },
    "Adult": {
        "heartrate": (60, 100),
        "resprate": (12, 20),
        "sbp": (90, 140),
        "dbp": (60, 90),
        "o2sat": (95, 100),
        "temperature": (97.0, 99.5),
    },
    "Geriatric": {
        # Geriatric patients decompensate faster and present atypically;
        # the upper HR/RR bound is tightened relative to adult so
        # early tachycardia/tachypnea in an elderly patient is not
        # silently treated as within-normal.
        "heartrate": (60, 90),
        "resprate": (12, 18),
        "sbp": (90, 140),
        "dbp": (60, 90),
        "o2sat": (94, 100),
        "temperature": (96.5, 99.0),
    },
    # Fallback used when age_group is "Unknown" — the widest (adult) band,
    # since we cannot apply an age-specific threshold without a known age.
    "Unknown": {
        "heartrate": (60, 100),
        "resprate": (12, 20),
        "sbp": (90, 140),
        "dbp": (60, 90),
        "o2sat": (95, 100),
        "temperature": (97.0, 99.5),
    },
}


# --------------------------------------------------------------------------- #
# Age
# --------------------------------------------------------------------------- #
def add_age_group(df: pd.DataFrame, age_col: str = "anchor_age") -> pd.DataFrame:
    """
    Bucket patient age into clinically meaningful triage cohorts.

    Clinical purpose
    -----------------
    ED triage protocols (e.g. ESI) apply different physiological
    thresholds and risk weighting to pediatric, adult, and geriatric
    patients (e.g. a heart rate of 110 is abnormal for an adult but can
    be normal for a young child; geriatric patients often present
    atypically and decompensate faster). Age-specific thresholds are a
    mandatory clinical safety requirement for this platform — every
    downstream vitals-abnormality check keys off this column.

    Categories
    ----------
    * Pediatric : age < 18
    * Adult     : 18 <= age < 65
    * Geriatric : age >= 65

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `age_col`.
    age_col : str
        Column holding patient age in years. Defaults to MIMIC's
        `anchor_age`; pass a different name if your merged frame uses one.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new `age_group` column. Missing/unparseable
        ages become "Unknown" rather than a guessed default — an unknown
        age must never be silently treated as "Adult".
    """
    df = df.copy()
    if age_col not in df.columns:
        logger.warning("Column '%s' not found — filling age_group with 'Unknown'.", age_col)
        df["age_group"] = "Unknown"
        return df

    bins = [-np.inf, 17, 64, np.inf]
    labels = ["Pediatric", "Adult", "Geriatric"]
    grouped = pd.cut(df[age_col], bins=bins, labels=labels, right=True)
    df["age_group"] = grouped.astype("object").fillna("Unknown")

    n_unknown = (df["age_group"] == "Unknown").sum()
    if n_unknown:
        logger.info("age_group: %d rows have unknown/missing age.", n_unknown)

    return df


# --------------------------------------------------------------------------- #
# Hemodynamic composite scores
# --------------------------------------------------------------------------- #
def add_shock_index(df: pd.DataFrame, hr_col: str = "heartrate", sbp_col: str = "sbp") -> pd.DataFrame:
    """
    Compute Shock Index = Heart Rate / Systolic Blood Pressure.

    Clinical purpose
    -----------------
    Shock Index is a well-validated early warning marker for occult
    hemorrhage, sepsis, and hemodynamic compromise — it flags
    deterioration *before* HR or BP individually cross alarming
    thresholds. A normal adult SI is ~0.5-0.7; SI > 0.9 is associated
    with increased mortality and need for critical intervention. Because
    under-triage is worse than over-triage, this feature is intentionally
    left as a continuous value (not pre-bucketed) so downstream modeling
    can weight the full range rather than a coarse cutoff.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `hr_col` and `sbp_col`.
    hr_col, sbp_col : str
        Column names for heart rate and systolic blood pressure.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with new `shock_index` column. Undefined (SBP<=0 or
        missing) values are set to NaN rather than raising or dividing by
        zero, so the pipeline never crashes on dirty vitals data — a NaN
        here should be treated as "unknown", which increases uncertainty
        rather than being imputed to a reassuring default.
    """
    df = df.copy()
    if hr_col not in df.columns or sbp_col not in df.columns:
        logger.warning("Missing '%s' or '%s' — shock_index set to NaN.", hr_col, sbp_col)
        df["shock_index"] = np.nan
        return df

    sbp_safe = df[sbp_col].replace(0, np.nan)
    df["shock_index"] = df[hr_col] / sbp_safe
    return df


def add_pulse_pressure(df: pd.DataFrame, sbp_col: str = "sbp", dbp_col: str = "dbp") -> pd.DataFrame:
    """
    Compute Pulse Pressure = Systolic BP - Diastolic BP.

    Clinical purpose
    -----------------
    Pulse pressure reflects arterial stiffness and stroke volume. A
    narrow pulse pressure (<25 mmHg) can indicate reduced cardiac output
    or hypovolemia; a widened pulse pressure (>60 mmHg) can indicate
    aortic regurgitation, sepsis, or arterial stiffening in the elderly.
    It's a cheap, vitals-only signal a nurse can act on immediately.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `sbp_col` and `dbp_col`.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new `pulse_pressure` column.
    """
    df = df.copy()
    if sbp_col not in df.columns or dbp_col not in df.columns:
        logger.warning("Missing '%s' or '%s' — pulse_pressure set to NaN.", sbp_col, dbp_col)
        df["pulse_pressure"] = np.nan
        return df

    df["pulse_pressure"] = df[sbp_col] - df[dbp_col]
    return df


def add_mean_arterial_pressure(df: pd.DataFrame, sbp_col: str = "sbp", dbp_col: str = "dbp") -> pd.DataFrame:
    """
    Compute Mean Arterial Pressure: MAP = DBP + (SBP - DBP) / 3.

    Clinical purpose
    -----------------
    MAP approximates average perfusion pressure delivered to organs
    across the cardiac cycle. MAP < 65 mmHg is a widely used threshold
    for inadequate organ perfusion (e.g. in sepsis resuscitation
    protocols) and is a stronger perfusion signal than SBP or DBP alone.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `sbp_col` and `dbp_col`.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new `mean_arterial_pressure` column.
    """
    df = df.copy()
    if sbp_col not in df.columns or dbp_col not in df.columns:
        logger.warning("Missing '%s' or '%s' — mean_arterial_pressure set to NaN.", sbp_col, dbp_col)
        df["mean_arterial_pressure"] = np.nan
        return df

    df["mean_arterial_pressure"] = df[dbp_col] + (df[sbp_col] - df[dbp_col]) / 3.0
    return df


# --------------------------------------------------------------------------- #
# Composite abnormality flags — AGE-AWARE (clinical safety requirement)
# --------------------------------------------------------------------------- #
def add_abnormal_vitals_count(
    df: pd.DataFrame,
    age_group_col: str = "age_group",
    ranges_by_age_group: dict[str, dict[str, tuple[float, float]]] | None = None,
) -> pd.DataFrame:
    """
    Count how many of the patient's vitals fall outside the NORMAL RANGE
    FOR THEIR AGE GROUP.

    Clinical purpose
    -----------------
    Single deranged vitals are common and often benign; MULTIPLE
    simultaneous deranged vitals are a strong, well-studied predictor of
    clinical deterioration and are the conceptual basis of early-warning
    scores (e.g. NEWS2, MEWS). Age-specific thresholds are mandatory:
    this function looks up each row's normal range by its `age_group`
    (see `add_age_group`) rather than applying one adult-only range to
    every patient — a heart rate that's alarming in a geriatric patient
    can be unremarkable in a child, and vice versa.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `age_group_col` (run `add_age_group` first) and the
        vital columns referenced in `ranges_by_age_group`.
    age_group_col : str
        Column holding "Pediatric" / "Adult" / "Geriatric" / "Unknown".
    ranges_by_age_group : dict, optional
        Nested mapping of age_group -> {vital_column: (low, high)}.
        Defaults to `NORMAL_RANGES_BY_AGE_GROUP`.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new integer `abnormal_vitals_count` column.
        Missing vital values are NOT counted as abnormal (treated as
        "unknown", not "deranged") to avoid penalizing incomplete
        charting — missingness is instead captured separately by
        `missing_history_flag` / null counts in the modeling layer.
    """
    df = df.copy()
    ranges_by_age_group = ranges_by_age_group or NORMAL_RANGES_BY_AGE_GROUP

    if age_group_col not in df.columns:
        logger.warning(
            "'%s' not found — run add_age_group() first. Falling back to 'Adult' "
            "ranges for all rows (logged as a safety-relevant fallback).",
            age_group_col,
        )
        age_groups = pd.Series("Adult", index=df.index)
    else:
        age_groups = df[age_group_col]

    vital_cols = sorted({col for ranges in ranges_by_age_group.values() for col in ranges})
    available_cols = [c for c in vital_cols if c in df.columns]
    missing_cols = [c for c in vital_cols if c not in df.columns]
    if missing_cols:
        logger.warning("abnormal_vitals_count: columns not found and skipped: %s", missing_cols)

    if not available_cols:
        df["abnormal_vitals_count"] = 0
        return df

    abnormal_flags = pd.DataFrame(index=df.index)
    for col in available_cols:
        low = age_groups.map(lambda g: ranges_by_age_group.get(g, ranges_by_age_group["Unknown"])[col][0])
        high = age_groups.map(lambda g: ranges_by_age_group.get(g, ranges_by_age_group["Unknown"])[col][1])
        is_abnormal = (df[col] < low) | (df[col] > high)
        is_abnormal = is_abnormal.where(df[col].notna(), other=False)
        abnormal_flags[col] = is_abnormal

    df["abnormal_vitals_count"] = abnormal_flags.sum(axis=1).astype(int)
    return df


def add_vitals_missing_count(
    df: pd.DataFrame,
    vital_cols: tuple[str, ...] = ("temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp"),
) -> pd.DataFrame:
    """
    Count how many of the core vitals are missing (NaN) for this stay.

    Clinical purpose
    -----------------
    This feature exists specifically to close a safety gap that
    `abnormal_vitals_count` cannot close on its own: that function
    deliberately does NOT count a missing vital as "abnormal" (so
    incomplete charting doesn't get penalized as if it were a bad
    reading) — but that means a stay with EVERY vital missing scores
    `abnormal_vitals_count == 0`, identical to a fully-documented,
    fully-normal patient. In practice this pattern shows up for the
    sickest patients in the data (e.g. cardiac/respiratory arrest,
    active seizure, intubated trauma) who bypass standard triage
    vitals collection because they go straight to resuscitation — the
    opposite of "unremarkable". `vitals_missing_count` makes that
    completeness gap an explicit, visible number so a model or nurse
    reviewing `abnormal_vitals_count == 0` can immediately see whether
    that means "checked and normal" or "never checked at all".

    Parameters
    ----------
    df : pd.DataFrame
        Table to check.
    vital_cols : tuple[str, ...]
        Core vitals to check for missingness.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new integer `vitals_missing_count` column
        (0 = all vitals documented, up to len(vital_cols) = none
        documented at all).
    """
    df = df.copy()
    available_cols = [c for c in vital_cols if c in df.columns]
    missing_requested = [c for c in vital_cols if c not in df.columns]
    if missing_requested:
        logger.warning("vitals_missing_count: columns not found and skipped: %s", missing_requested)

    if not available_cols:
        df["vitals_missing_count"] = len(vital_cols)
        return df

    df["vitals_missing_count"] = df[available_cols].isna().sum(axis=1).astype(int)

    n_fully_missing = int((df["vitals_missing_count"] == len(available_cols)).sum())
    if n_fully_missing:
        logger.warning(
            "vitals_missing_count: %d stays have ZERO documented vitals — "
            "these are NOT the same as 'normal vitals' and must not be "
            "treated as low-acuity on the strength of abnormal_vitals_count alone.",
            n_fully_missing,
        )
    return df


def add_missing_history_flag(
    df: pd.DataFrame, history_cols: Iterable[str] = ("chiefcomplaint",)
) -> pd.DataFrame:
    """
    Flag encounters with incomplete clinical history at triage.

    Clinical purpose
    -----------------
    A missing chief complaint (or other key history field) is itself a
    signal — it can indicate an altered-mental-status patient, a language
    barrier, an unaccompanied minor, or simply rushed/incomplete triage
    documentation. Missing data increases uncertainty, not confidence:
    this flag makes that uncertainty explicit to downstream models and
    reviewing nurses rather than letting a blank field pass silently.

    Zero-history patients are PRESERVED, never dropped: this function
    only flags, it never filters rows out of the dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Table to check.
    history_cols : Iterable[str]
        Column(s) considered part of "history" documentation. If ANY of
        these is null/empty for a row, `missing_history_flag` is set to 1.

    Returns
    -------
    pd.DataFrame
        Copy of `df` (same row count as input — no rows removed) with a
        new binary `missing_history_flag` column (1 = at least one
        history field missing, 0 = fully documented).
    """
    df = df.copy()
    present_cols = [c for c in history_cols if c in df.columns]
    missing_requested = [c for c in history_cols if c not in df.columns]

    if missing_requested:
        logger.warning(
            "missing_history_flag: requested columns not in df and skipped: %s", missing_requested
        )

    if not present_cols:
        # If we can't check any history column, be conservative and flag
        # every row rather than guessing — consistent with "missing data
        # increases uncertainty".
        df["missing_history_flag"] = 1
        return df

    def _is_blank(series: pd.Series) -> pd.Series:
        if series.dtype == object:
            return series.isna() | (series.astype(str).str.strip() == "")
        return series.isna()

    blank_mask = pd.concat([_is_blank(df[c]) for c in present_cols], axis=1).any(axis=1)
    df["missing_history_flag"] = blank_mask.astype(int)

    n_flagged = int(df["missing_history_flag"].sum())
    if n_flagged:
        logger.info(
            "missing_history_flag: %d/%d rows flagged with incomplete history (preserved, not dropped).",
            n_flagged,
            len(df),
        )
    return df


# --------------------------------------------------------------------------- #
# Temporal features
# --------------------------------------------------------------------------- #
def add_arrival_hour(df: pd.DataFrame, arrival_col: str = "intime") -> pd.DataFrame:
    """
    Extract the hour-of-day (0-23) a patient arrived in the ED.

    Clinical purpose
    -----------------
    ED census, staffing ratios, and case-mix vary predictably by hour
    (e.g. trauma/intoxication spikes overnight, pediatric fever spikes in
    evenings). Arrival hour helps the model contextualize acuity against
    typical departmental load and patient-mix at that time.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `arrival_col` as a datetime or datetime-parseable
        string column (MIMIC-IV-ED's `intime`).
    arrival_col : str
        Column holding ED arrival timestamp.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new integer `arrival_hour` column (0-23), or
        NaN where the timestamp could not be parsed.
    """
    df = df.copy()
    if arrival_col not in df.columns:
        logger.warning("Column '%s' not found — arrival_hour set to NaN.", arrival_col)
        df["arrival_hour"] = np.nan
        return df

    parsed = pd.to_datetime(df[arrival_col], errors="coerce")
    n_unparsed = int(parsed.isna().sum() - df[arrival_col].isna().sum())
    if n_unparsed > 0:
        logger.warning(
            "arrival_hour: %d values in '%s' could not be parsed as datetime.", n_unparsed, arrival_col
        )
    df["arrival_hour"] = parsed.dt.hour
    return df


def add_night_shift_flag(df: pd.DataFrame, arrival_hour_col: str = "arrival_hour") -> pd.DataFrame:
    """
    Flag arrivals during the overnight shift (23:00-06:59).

    Clinical purpose
    -----------------
    Night-shift EDs typically run with leaner staffing and fewer
    ancillary services (e.g. limited specialist coverage, slower lab
    turnaround), and night-shift patients skew toward higher-acuity
    presentations (trauma, intoxication, psychiatric crises). This flag
    lets the model account for a systematically different care context.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `arrival_hour_col` (see `add_arrival_hour`).

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new nullable-integer `night_shift_flag`
        column (1 = arrival between 23:00-06:59, 0 = daytime/evening,
        <NA> where arrival hour is unknown).
    """
    df = df.copy()
    if arrival_hour_col not in df.columns:
        logger.warning(
            "Column '%s' not found — call add_arrival_hour() first. night_shift_flag set to NaN.",
            arrival_hour_col,
        )
        df["night_shift_flag"] = np.nan
        return df

    hour = df[arrival_hour_col]
    is_night = (hour >= 23) | (hour < 7)
    df["night_shift_flag"] = is_night.where(hour.notna(), other=np.nan).astype("Int64")
    return df


def add_weekend_flag(df: pd.DataFrame, arrival_col: str = "intime") -> pd.DataFrame:
    """
    Flag ED arrivals occurring on a Saturday or Sunday.

    Clinical purpose
    -----------------
    Weekend EDs often have reduced access to primary/specialty care in
    the community, driving different (and sometimes delayed, more acute)
    presentations, and hospitals frequently run reduced weekend staffing
    (the "weekend effect" widely documented in outcomes literature). This
    flag lets the model condition on that systematic difference.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `arrival_col` as a datetime or datetime-parseable
        string column.
    arrival_col : str
        Column holding ED arrival timestamp.

    Returns
    -------
    pd.DataFrame
        Copy of `df` with a new nullable-integer `weekend_flag` column
        (1 = Saturday/Sunday, 0 = weekday, <NA> if unparseable).
    """
    df = df.copy()
    if arrival_col not in df.columns:
        logger.warning("Column '%s' not found — weekend_flag set to NaN.", arrival_col)
        df["weekend_flag"] = np.nan
        return df

    parsed = pd.to_datetime(df[arrival_col], errors="coerce")
    is_weekend = parsed.dt.dayofweek.isin([5, 6])  # 5=Saturday, 6=Sunday
    df["weekend_flag"] = is_weekend.where(parsed.notna(), other=np.nan).astype("Int64")
    return df


# --------------------------------------------------------------------------- #
# Convenience: apply the full engineered feature set in one call
# --------------------------------------------------------------------------- #
def engineer_all_features(
    df: pd.DataFrame,
    age_col: str = "anchor_age",
    hr_col: str = "heartrate",
    sbp_col: str = "sbp",
    dbp_col: str = "dbp",
    arrival_col: str = "intime",
    history_cols: Iterable[str] = ("chiefcomplaint",),
) -> pd.DataFrame:
    """
    Apply every engineered feature in this module, in dependency order.

    `add_age_group` runs first because `add_abnormal_vitals_count`
    depends on it for age-specific thresholds; `add_arrival_hour` runs
    before `add_night_shift_flag` for the same reason.

    Parameters
    ----------
    df : pd.DataFrame
        Merged edstays + triage frame (see `preprocess.merge_core_tables`).
    age_col, hr_col, sbp_col, dbp_col, arrival_col : str
        Source column overrides, passed through to individual feature
        functions.
    history_cols : Iterable[str]
        Columns checked by `add_missing_history_flag`.

    Returns
    -------
    pd.DataFrame
        `df` (same row count — no rows dropped) with all engineered
        clinical features appended.
    """
    rows_in = len(df)
    logger.info("Engineering clinical features on frame with shape=%s", df.shape)

    df = add_age_group(df, age_col=age_col)
    df = add_shock_index(df, hr_col=hr_col, sbp_col=sbp_col)
    df = add_pulse_pressure(df, sbp_col=sbp_col, dbp_col=dbp_col)
    df = add_mean_arterial_pressure(df, sbp_col=sbp_col, dbp_col=dbp_col)
    df = add_abnormal_vitals_count(df)
    df = add_vitals_missing_count(df)
    df = add_missing_history_flag(df, history_cols=history_cols)
    df = add_arrival_hour(df, arrival_col=arrival_col)
    df = add_night_shift_flag(df, arrival_hour_col="arrival_hour")
    df = add_weekend_flag(df, arrival_col=arrival_col)

    assert len(df) == rows_in, "Feature engineering must never change row count (zero-history patients preserved)."
    logger.info("Feature engineering complete. Final shape=%s", df.shape)
    return df
