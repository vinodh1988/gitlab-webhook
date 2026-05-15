from __future__ import annotations

import asyncio
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class WebhookStore:
    def __init__(self, max_events: int = 1000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._counter_by_event: Counter[str] = Counter()
        self._counter_by_project: Counter[str] = Counter()
        self._counter_by_author: Counter[str] = Counter()
        self._counter_by_source: Counter[str] = Counter()
        self._websockets: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._events.appendleft(event)
            self._counter_by_event[event["event_type"]] += 1
            self._counter_by_project[event["project"]] += 1
            self._counter_by_author[event["author"]] += 1
            self._counter_by_source[event["source"]] += 1
            stats = self._build_stats_locked()

        await self.broadcast({"type": "new_event", "event": event, "stats": stats})
        return stats

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                "events": list(self._events),
                "stats": self._build_stats_locked(),
            }

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._websockets.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._websockets.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._websockets)

        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._websockets.discard(ws)

    def _build_stats_locked(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "connections": len(self._websockets),
            "by_event_type": dict(self._counter_by_event),
            "by_project": dict(self._counter_by_project),
            "by_author": dict(self._counter_by_author),
            "by_source": dict(self._counter_by_source),
        }
