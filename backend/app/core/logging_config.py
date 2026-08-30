"""
core/logging_config.py
========================

PatientTriage.ai — Logging Configuration
-------------------------------------------
Centralized logging setup. Clinical decision-support systems must have
traceable, timestamped logs — this is foundational for the audit trail
requirement ("every recommendation must be reviewable, overridable, and
audit logged"), even though the audit-logging *business logic* itself
lands in a later milestone.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    """
    Configure the root logger once, at application startup.

    Idempotent: calling this multiple times (e.g. in tests that import
    the app repeatedly) will not create duplicate log handlers.
    """
    settings = get_settings()
    root_logger = logging.getLogger()

    if root_logger.handlers:
        # Already configured (e.g. by a previous import in the same process).
        root_logger.setLevel(settings.LOG_LEVEL)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL)

    # Quiet down noisy third-party loggers by default.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience accessor so modules can do `logger = get_logger(__name__)`
    without importing `logging` directly everywhere.
    """
    return logging.getLogger(name)
