from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/drift/{model_id}")
async def websocket_drift_endpoint(websocket: WebSocket, model_id: str):
    await websocket.accept()
    await websocket.send_json({"model_id": model_id, "message": "drift socket connected"})
    await websocket.close()