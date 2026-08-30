"""
models package
================

Import every ORM model here so that `Base.metadata` (and therefore Alembic
`--autogenerate`) is aware of the full schema regardless of which module
happens to trigger the import first.

Milestone 1 shipped only the audit log. Milestone 3 adds `TriageStay`,
the clinically-readable ED-stay table backing the dashboard and the
model-scoring endpoints (see `app/models/triage_stay.py` for why it does
not mirror `data/processed_triage.csv` column-for-column).
"""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.triage_stay import TriageStay  # noqa: F401

__all__ = ["AuditLog", "TriageStay"]
