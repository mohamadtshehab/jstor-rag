from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..dependencies import get_notification
from ..utilities.notification_utility import NotificationUtility

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    notification: NotificationUtility = Depends(get_notification),
) -> None:
    await ws.accept()
    notification.register_ws(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        notification.unregister_ws(ws)
