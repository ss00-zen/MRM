from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.core.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/models")
async def ws_models(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(10)   # ✅ KEEP CONNECTION ALIVE
    except WebSocketDisconnect:
        manager.disconnect(websocket)
