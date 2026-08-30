"""
api/router.py
===============

PatientTriage.ai — API Router Aggregation
---------------------------------------------
Single place that wires every route module into one `APIRouter`, which
`app/main.py` mounts under `settings.API_V1_PREFIX`. Adding a new route
module in future milestones means: write the module, import it here,
`include_router` it — nothing in `main.py` changes.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import audit, health, model, override, queue, triage, triage_stays, vitals
from app.api import security

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(triage_stays.router)
api_router.include_router(model.router)
api_router.include_router(triage.router)
api_router.include_router(queue.router)
api_router.include_router(override.router)
api_router.include_router(vitals.router)
api_router.include_router(audit.router)
api_router.include_router(security.router)
