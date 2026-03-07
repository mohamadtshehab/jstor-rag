from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Callable

from fastapi import WebSocket

from ..contracts.interfaces import INotificationUtility

logger = logging.getLogger(__name__)

Callback = Callable[[dict], object]


class NotificationUtility(INotificationUtility):
    """WebSocket-based publish / subscribe for async state broadcasting.

    Hides the transport layer (WebSocket today, Redis Pub/Sub tomorrow)
    behind a generic publish/subscribe interface.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callback]] = defaultdict(list)
        self._ws_clients: list[WebSocket] = []

    async def publish(self, event: str, data: dict) -> None:
        message = json.dumps({"event": event, "data": data})

        stale: list[WebSocket] = []
        for ws in self._ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._ws_clients.remove(ws)

        for cb in self._subscribers.get(event, []):
            try:
                result = cb(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Subscriber callback error for event %s", event)

    async def subscribe(self, event: str, callback: Callback) -> None:
        self._subscribers[event].append(callback)

    def register_ws(self, ws: WebSocket) -> None:
        self._ws_clients.append(ws)

    def unregister_ws(self, ws: WebSocket) -> None:
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)
