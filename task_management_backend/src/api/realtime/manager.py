import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages active websocket connections and broadcasts JSON messages."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all active connections; drop dead sockets."""
        payload = json.dumps(message, default=str)
        async with self._lock:
            sockets = list(self._active)

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._active.discard(ws)


manager = ConnectionManager()
