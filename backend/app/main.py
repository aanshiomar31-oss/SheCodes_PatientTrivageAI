"""
app/main.py
=============

PatientTriage.ai — FastAPI Application Entrypoint
------------------------------------------------------
Creates and configures the FastAPI app: CORS, structured logging,
database table creation (dev convenience — production schema changes go
through Alembic, see `backend/alembic/`), the versioned REST API router,
and a foundational WebSocket endpoint for future real-time updates.

Governing rule: "The AI recommends. The nurse decides." This module
wires infrastructure only — no clinical decision logic lives here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging_config import configure_logging, get_logger
from app.schemas.health import RootResponse
from app.services.monitor import run_monitor_loop
from app.websocket.connection_manager import manager

# Import models so their tables are registered on `Base.metadata`
# before `create_all` runs below.
import app.models  # noqa: F401
import asyncio

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    On startup: ensure the SQLite database file/tables exist (development
    convenience only — real schema evolution is Alembic's job), and start
    the waiting-room monitor as a background task (see
    `app/services/monitor.py`).
    On shutdown: cancel the monitor task cleanly and log a shutdown message.
    """
    logger.info("Starting %s (%s environment)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured at %s", settings.DATABASE_URL)

    monitor_task = asyncio.create_task(run_monitor_loop())

    yield

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """
    Application factory. Keeping this as a factory (rather than a bare
    module-level `app = FastAPI()`) makes the app easy to re-instantiate
    with different settings in tests.
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Clinical Decision Support System for Emergency Department triage. "
            "The AI recommends. The nurse decides."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()


@app.get("/", response_model=RootResponse, tags=["root"])
def root() -> RootResponse:
    """Root endpoint — quick sanity check that the API is up."""
    return RootResponse(
        message=f"{settings.PROJECT_NAME} API is running.",
        docs_url="/docs",
    )


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    """
    Live event feed. Broadcasts: new_patient (POST /triage), override
    (POST /override), vitals_updated (POST /vitals/update), and
    reassessment_alert (the background waiting-room monitor). See
    `app/websocket/connection_manager.py` for the broadcast mechanism
    and each route module for its specific event payload shape.
    """
    await manager.connect(websocket)
    try:
        await manager.send_personal_message(
            {"event": "connection_ack", "message": "Connected to PatientTriage.ai live feed."},
            websocket,
        )
        while True:
            # Clients don't need to send anything; keep the socket alive
            # and tolerate whatever they do send (e.g. ping frames).
            data = await websocket.receive_text()
            logger.debug("WebSocket received message: %s", data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
