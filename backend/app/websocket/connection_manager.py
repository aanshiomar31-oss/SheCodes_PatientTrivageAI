"""
websocket/connection_manager.py
==================================

PatientTriage.ai — WebSocket Connection Manager
----------------------------------------------------
Generic infrastructure for tracking connected WebSocket clients and
broadcasting messages to them (e.g. a future "queue updated" or
"new recommendation available" event). Contains no clinical logic —
what gets broadcast, and when, is defined by later milestones.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import WebSocket

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Tracks active WebSocket connections and provides broadcast helpers.

    Thread-safety note: FastAPI/Starlette runs the event loop
    single-threaded per worker process, so a plain list is safe here.
    If this is ever used across multiple worker processes, connections
    must be tracked in a shared store (e.g. Redis pub/sub) instead.
    """

    def __init__(self) -> None:
        self._active_connections: List[WebSocket] = []
        self._MAX_CONNECTIONS = 10  # cap to prevent event-loop saturation

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and start tracking it."""
        if len(self._active_connections) >= self._MAX_CONNECTIONS:
            await websocket.close(code=1008)  # Policy Violation — too many connections
            logger.warning("WebSocket rejected: at connection cap (%d)", self._MAX_CONNECTIONS)
            return
        await websocket.accept()
        self._active_connections.append(websocket)
        logger.info("WebSocket connected. Active connections: %d", len(self._active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Stop tracking a WebSocket connection (call on disconnect/error)."""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Active connections: %d", len(self._active_connections))

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a JSON-serializable message to a single client."""
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Send a JSON-serializable message to every connected client.

        Dead connections encountered during broadcast are removed rather
        than allowed to raise and break the loop for other clients.
        """
        stale: List[WebSocket] = []
        for connection in self._active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:  # noqa: BLE001 — never let one bad socket break broadcast
                logger.warning("Failed to send to a WebSocket client, marking stale: %s", exc)
                stale.append(connection)

        for connection in stale:
            self.disconnect(connection)

    @property
    def active_connection_count(self) -> int:
        return len(self._active_connections)


# Module-level singleton shared across the app (imported by main.py and
# any future route/service that needs to push real-time updates).
manager = ConnectionManager()
