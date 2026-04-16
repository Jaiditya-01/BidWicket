import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """Generic WebSocket manager keyed by room_id (match_id or auction_id)."""

    def __init__(self):
        self._rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self._rooms.setdefault(room_id, []).append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self._rooms:
            self._rooms[room_id].discard(websocket) if hasattr(self._rooms[room_id], "discard") else None
            try:
                self._rooms[room_id].remove(websocket)
            except ValueError:
                pass
            if not self._rooms[room_id]:
                del self._rooms[room_id]

    async def broadcast(self, room_id: str, payload: dict):
        """Send JSON payload to all connections in the room."""
        dead: List[WebSocket] = []
        for ws in self._rooms.get(room_id, []):
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(room_id, ws)

    async def send_personal(self, websocket: WebSocket, payload: dict):
        await websocket.send_text(json.dumps(payload, default=str))

    def room_size(self, room_id: str) -> int:
        return len(self._rooms.get(room_id, []))


# Singleton managers — one per domain
match_manager = ConnectionManager()
auction_manager = ConnectionManager()
