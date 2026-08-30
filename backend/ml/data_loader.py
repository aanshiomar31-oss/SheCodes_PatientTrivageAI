"""
ml/data_loader.py
===================

PatientTriage.ai — Clinical Data Loader
------------------------------------------
Loads and validates the raw MIMIC-IV-ED (Demo) source tables that the
rest of the data pipeline (`features.py`, `preprocess.py`) builds on.

Integrates with the existing backend architecture rather than
reinventing it: paths come from `app.core.config.get_settings()`
(`DATA_DIR`), and logging goes through `app.core.logging_config`, so log
output from this module is formatted identically to the FastAPI app's.

Design goals
------------
* Never let one missing/corrupted file crash the whole pipeline — log
  the problem clearly and continue with whatever CAN be loaded.
* Fail loudly via logging (never a silent `except: pass`).
* Return typed, schema-validated `pandas.DataFrame`s only — no modeling
  or feature-engineering logic lives here (that's `features.py`).

Clinical safety note: missing data increases uncertainty, it is never
treated as "normal" — this module surfaces missingness, it never masks it.
"The AI recommends. The nurse decides."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Schema definitions
# --------------------------------------------------------------------------- #
# Required columns per MIMIC-IV-ED demo table — the minimal columns the
# downstream feature engineering / preprocessing steps depend on.
REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "edstays": [
        "subject_id",
        "hadm_id",
        "stay_id",
        "intime",
        "outtime",
        "gender",
        "race",
        "arrival_transport",
        "disposition",
    ],
    "triage": [
        "subject_id",
        "stay_id",
        "temperature",
        "heartrate",
        "resprate",
        "o2sat",
        "sbp",
        "dbp",
        "pain",
        "acuity",
        "chiefcomplaint",
    ],
    "vitalsign": [
        "subject_id",
        "stay_id",
        "charttime",
        "temperature",
        "heartrate",
        "resprate",
        "o2sat",
        "sbp",
        "dbp",
        "rhythm",
        "pain",
    ],
    "diagnosis": [
        "subject_id",
        "stay_id",
        "seq_num",
        "icd_code",
        "icd_version",
        "icd_title",
    ],
    "medrecon": [
        "subject_id",
        "stay_id",
        "charttime",
        "name",
        "gsn",
    ],
    "pyxis": [
        "subject_id",
        "stay_id",
        "charttime",
        "name",
        "gsn_rn",
        "gsn",
    ],
}

# Default file names as shipped with the MIMIC-IV-ED demo dataset.
DEFAULT_FILENAMES: Dict[str, str] = {
    "edstays": "edstays.csv.gz",
    "triage": "triage.csv.gz",
    "vitalsign": "vitalsign.csv.gz",
    "diagnosis": "diagnosis.csv.gz",
    "medrecon": "medrecon.csv.gz",
    "pyxis": "pyxis.csv.gz",
}

# Explicit dtypes for identifier columns shared across tables. Keeping IDs
# as nullable Int64 (not float64) avoids the classic "1000 becomes
# 1000.0 becomes '1000.0'" bug when a table has any missing IDs.
_ID_DTYPES = {
    "subject_id": "Int64",
    "hadm_id": "Int64",
    "stay_id": "Int64",
}


@dataclass
class LoadReport:
    """Summary of what happened during a `load_all_tables` call."""

    loaded: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    corrupted_files: List[str] = field(default_factory=list)
    missing_columns: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True only if every table loaded cleanly with no issues."""
        return not (self.missing_files or self.corrupted_files or self.missing_columns)

    def summary(self) -> str:
        return (
            f"Loaded OK: {self.loaded}\n"
            f"Missing files: {self.missing_files or 'none'}\n"
            f"Corrupted files: {self.corrupted_files or 'none'}\n"
            f"Missing columns: {self.missing_columns or 'none'}"
        )


# --------------------------------------------------------------------------- #
# Core functions
# --------------------------------------------------------------------------- #
def validate_file_exists(file_path: Path) -> bool:
    """
    Check that a data file exists and is non-empty on disk.

    Parameters
    ----------
    file_path : Path
        Path to the expected `.csv.gz` file.

    Returns
    -------
    bool
        True if the file exists and has non-zero size, False otherwise.
    """
    if not file_path.exists():
        logger.error("Missing data file: %s", file_path)
        return False
    if file_path.stat().st_size == 0:
        logger.error("Data file exists but is empty (0 bytes): %s", file_path)
        return False
    return True


def validate_required_columns(
    df: pd.DataFrame, table_name: str, required_columns: List[str]
) -> List[str]:
    """
    Check a loaded DataFrame for the presence of required columns.

    Parameters
    ----------
    df : pd.DataFrame
        The loaded table.
    table_name : str
        Logical name of the table (for logging), e.g. "triage".
    required_columns : List[str]
        Columns that MUST be present for downstream steps to work safely.

    Returns
    -------
    List[str]
        List of missing column names (empty list means fully valid).
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logger.warning("Table '%s' is missing required columns: %s", table_name, missing)
    return missing


def _apply_id_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Cast known identifier columns to nullable Int64 where present."""
    for col, dtype in _ID_DTYPES.items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dtype)
            except (TypeError, ValueError) as exc:
                logger.warning("Could not cast column '%s' to %s: %s", col, dtype, exc)
    return df


def load_single_table(
    data_dir: Path,
    table_name: str,
    filename: Optional[str] = None,
    required_columns: Optional[List[str]] = None,
) -> Optional[pd.DataFrame]:
    """
    Load and validate a single MIMIC-IV-ED table.

    Handles missing files and corrupted/unreadable CSVs gracefully by
    logging the error and returning None rather than raising, so one bad
    file can never bring down the whole loading process.

    Parameters
    ----------
    data_dir : Path
        Directory containing the raw `.csv.gz` files.
    table_name : str
        Logical table name, e.g. "edstays". Used to look up the default
        filename and required-column schema if not explicitly supplied.
    filename : Optional[str]
        Override for the file name. Defaults to `DEFAULT_FILENAMES[table_name]`.
    required_columns : Optional[List[str]]
        Override for required columns. Defaults to `REQUIRED_COLUMNS[table_name]`.

    Returns
    -------
    Optional[pd.DataFrame]
        The loaded, typed DataFrame, or None if the file was missing/corrupted.
    """
    filename = filename or DEFAULT_FILENAMES.get(table_name, f"{table_name}.csv.gz")
    required_columns = required_columns if required_columns is not None else REQUIRED_COLUMNS.get(table_name, [])
    file_path = data_dir / filename

    if not validate_file_exists(file_path):
        return None

    try:
        df = pd.read_csv(file_path, compression="gzip", low_memory=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        logger.error("Corrupted/unreadable CSV for table '%s': %s — %s", table_name, file_path, exc)
        return None
    except OSError as exc:
        logger.error("OS error while reading '%s': %s — %s", table_name, file_path, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — deliberately broad: never crash the pipeline
        logger.error("Unexpected error loading '%s' from %s: %s", table_name, file_path, exc)
        return None

    if df.empty:
        logger.warning("Table '%s' loaded but contains zero rows.", table_name)

    df = _apply_id_dtypes(df)

    missing_cols = validate_required_columns(df, table_name, required_columns)
    if missing_cols:
        # Returned anyway — the caller decides whether a partial schema is
        # tolerable — but flagged via df.attrs so LoadReport can record it.
        df.attrs["missing_columns"] = missing_cols

    logger.info("Loaded table '%s' from %s — shape=%s", table_name, file_path.name, df.shape)
    return df


def load_all_tables(data_dir: Optional[str | Path] = None) -> tuple[Dict[str, pd.DataFrame], LoadReport]:
    """
    Load all MIMIC-IV-ED demo tables required by PatientTriage.ai.

    Parameters
    ----------
    data_dir : Optional[str | Path]
        Directory containing the raw `.csv.gz` files. Defaults to the
        existing app's configured `settings.DATA_DIR`
        (`backend/app/core/config.py`) so this module never drifts from
        where the rest of the application expects data to live.

    Returns
    -------
    tuple[Dict[str, pd.DataFrame], LoadReport]
        * dict mapping table name -> loaded DataFrame (only for tables
          that loaded successfully; missing/corrupted tables are simply
          absent from this dict, never present as None).
        * LoadReport summarizing what succeeded / failed.
    """
    settings = get_settings()
    data_dir = Path(data_dir) if data_dir is not None else settings.DATA_DIR

    logger.info("Starting clinical data load from directory: %s", data_dir.resolve())

    report = LoadReport()
    tables: Dict[str, pd.DataFrame] = {}

    if not data_dir.exists():
        logger.error("Data directory does not exist: %s", data_dir.resolve())
        report.missing_files = list(DEFAULT_FILENAMES.values())
        return tables, report

    for table_name, filename in DEFAULT_FILENAMES.items():
        file_path = data_dir / filename

        if not validate_file_exists(file_path):
            report.missing_files.append(filename)
            continue

        df = load_single_table(data_dir, table_name)

        if df is None:
            report.corrupted_files.append(filename)
            continue

        missing_cols = df.attrs.get("missing_columns", [])
        if missing_cols:
            report.missing_columns[table_name] = missing_cols

        tables[table_name] = df
        report.loaded.append(table_name)

    logger.info("Clinical data load complete.\n%s", report.summary())
    return tables, report


# --------------------------------------------------------------------------- #
# Manual run / smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    tables_loaded, load_report = load_all_tables()

    print("\n=== PatientTriage.ai — Data Loader Smoke Test ===")
    for name, frame in tables_loaded.items():
        print(f"  {name:<12} shape={frame.shape}")

    if not load_report.ok:
        print("\nWarnings/Errors encountered:")
        print(load_report.summary())
