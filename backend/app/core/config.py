"""
core/config.py
===============

PatientTriage.ai — Application Settings
-----------------------------------------
Single source of truth for configuration. Values are read from the
environment (and a local `.env` file, see `.env.example`) via
`pydantic-settings`, never hard-coded elsewhere in the app.

Governing rule reminder: "The AI recommends. The nurse decides."
This module is pure configuration — it contains no clinical logic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = PatientTriageAI/backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Typed application settings.

    Every field has a safe local-development default so the app can boot
    with zero configuration, but production deployments MUST override
    `SECRET_KEY`, `DATABASE_URL`, and `CORS_ORIGINS` via environment
    variables or a mounted `.env` file — never commit real secrets.
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General -----------------------------------------------------
    PROJECT_NAME: str = "PatientTriage.ai"
    ENVIRONMENT: str = "development"  # development | staging | production
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Security ------------------------------------------------------
    SECRET_KEY: str = "CHANGE_ME_INSECURE_DEV_ONLY_SECRET_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Database ------------------------------------------------------
    # SQLite by default for local dev / demo; override with a Postgres
    # URL etc. in production via DATABASE_URL.
    DATABASE_URL: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'patient_triage.db'}"

    # --- CORS ------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Data paths ------------------------------------------------------
    DATA_DIR: Path = BACKEND_ROOT / "data"
    REPORTS_DIR: Path = BACKEND_ROOT / "reports"

    # --- MLflow ------------------------------------------------------------
    MLFLOW_TRACKING_URI: str = f"file:{BACKEND_ROOT / 'reports' / 'mlruns'}"
    MLFLOW_EXPERIMENT_NAME: str = "patient_triage_ai"

    # --- WebSocket ------------------------------------------------------------
    WS_HEARTBEAT_SECONDS: int = 30

    # --- Logging ------------------------------------------------------------
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached `Settings` instance.

    Cached (via `lru_cache`) so environment/`.env` parsing only happens
    once per process, and every module gets the same settings object.
    """
    return Settings()
