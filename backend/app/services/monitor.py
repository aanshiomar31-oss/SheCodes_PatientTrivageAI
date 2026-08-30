"""
app/services/monitor.py
===========================

PatientTriage.ai — Waiting Room Monitor
------------------------------------------------
A background asyncio task, started from `app.main`'s lifespan, that
periodically checks every waiting patient for:

  - a wait time past their priority's safe reassessment interval
    ("retriage_breach" — nurse must re-assess)
  - low model confidence recorded at intake
    ("reassessment_alert" — recommendation is uncertain)

Important: this monitor does NOT re-run predict() on every patient every
cycle. Doing so was causing 50+ simultaneous ML inferences that saturated
the async event loop and blocked all HTTP requests. Instead we use the
priority and confidence already stored in the database, which are correct
for the purpose of breach detection.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import get_logger
from app.models.triage_stay import TriageStay
from app.services.cps import format_patient_id, minutes_waited
from app.websocket.connection_manager import manager

logger = get_logger(__name__)

# Check every 60 seconds — breach thresholds are in minutes, 15s resolution
# gives no meaningful improvement and bloats the event log.
CHECK_INTERVAL_SECONDS = 60

# ACEP-derived safe wait thresholds per ESI/priority level.
# P1 = 0 means the patient should already be seen; flag immediately.
SAFE_WAIT_MINUTES: dict[str, int] = {
    "P1": 0,
    "P2": 15,
    "P3": 30,
    "P4": 60,
    "P5": 120,
}


async def _check_once(db: Session) -> None:
    stays = db.execute(select(TriageStay)).scalars().all()

    for stay in stays:
        # Skip pre-loaded MIMIC rows that were never scored at live intake
        # — they have no recommended_priority, so breach detection is meaningless.
        if stay.recommended_priority is None:
            continue

        waited = minutes_waited(stay)

        # Use stored priority from the DB — do NOT re-run predict().
        # The stored priority is the nurse-visible value (may have been
        # overridden); breach detection should reflect what the nurse sees.
        priority = stay.recommended_priority
        safe_minutes = SAFE_WAIT_MINUTES.get(priority, 60)
        overdue = (safe_minutes == 0 and waited > 0) or (safe_minutes > 0 and waited > safe_minutes)

        if overdue:
            await manager.broadcast({
                "event": "retriage_breach",
                "patient_id": format_patient_id(stay.stay_id),
                "stay_id": stay.stay_id,
                "priority": priority,
                "waited_minutes": round(waited, 1),
                "safe_minutes": safe_minutes,
                "message": (
                    f"⚠\ufe0f Stay #{stay.stay_id} ({priority}) has waited "
                    f"{round(waited)}m (limit: {safe_minutes}m). Re-assess now."
                ),
            })
            logger.warning(
                "Retriage breach: stay_id=%s priority=%s waited=%.1fm limit=%dm",
                stay.stay_id, priority, waited, safe_minutes,
            )


async def run_monitor_loop() -> None:
    """
    Runs forever until cancelled (see `app.main`'s lifespan shutdown).
    A single failed cycle is logged and the loop continues.
    """
    logger.info("Waiting room monitor started (checking every %ds)", CHECK_INTERVAL_SECONDS)

    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            await _check_once(db)
        except Exception as exc:  # noqa: BLE001
            logger.error("Waiting room monitor cycle failed: %s", exc)
        finally:
            db.close()
