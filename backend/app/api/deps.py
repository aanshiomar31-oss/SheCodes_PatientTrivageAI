"""
api/deps.py
=============

PatientTriage.ai — Shared API Dependencies
-----------------------------------------------
Central place for FastAPI `Depends()` callables shared across route
modules, so route files import from one place instead of reaching into
`app.core.*` directly. Authentication/authorization dependencies
(e.g. `get_current_nurse`) will be added here in the security milestone.
"""

from __future__ import annotations

from app.core.database import get_db

__all__ = ["get_db"]
