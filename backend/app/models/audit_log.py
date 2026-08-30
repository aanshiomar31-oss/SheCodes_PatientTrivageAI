"""
models/audit_log.py
=====================

PatientTriage.ai — Audit Log Model
-------------------------------------
Foundational persistence model backing the platform's governing rule:

    "The AI recommends. The nurse decides."
    Every recommendation must be reviewable, overridable, and audit logged.

This milestone defines the SCHEMA only — the service layer that writes
audit entries when a recommendation is shown, overridden, or accepted is
business logic for a later milestone. The table exists now so Alembic can
manage it from day one and no future migration has to retrofit it under
live clinical data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp factory (avoids naive `datetime.utcnow`)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    """
    Immutable record of a clinically-relevant system event.

    Rows are intended to be append-only: nothing in this application layer
    should ever UPDATE or DELETE an `AuditLog` row. Enforcing that at the
    database/permissions layer is a deployment-hardening task for a later
    milestone.

    Columns
    -------
    id : str
        UUID4 primary key.
    event_type : str
        Machine-readable event category, e.g.
        "recommendation_shown", "recommendation_overridden",
        "recommendation_accepted", "manual_triage_entry".
    actor : str
        Identifier of the human or system component responsible for the
        event (e.g. a nurse's user id, or "system" for automated events).
    resource_type : str
        The kind of entity the event relates to, e.g. "triage_stay".
    resource_id : str
        Identifier of the specific entity instance (e.g. a `stay_id`).
    details : str | None
        Free-text / JSON-encoded context about the event. Kept as `Text`
        rather than a structured column set at this stage since the exact
        payload shape is defined by the business logic milestone that
        writes to this table.
    created_at : datetime
        UTC timestamp the event was recorded, set automatically.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return (
            f"<AuditLog id={self.id} event_type={self.event_type!r} "
            f"actor={self.actor!r} resource={self.resource_type}:{self.resource_id}>"
        )
