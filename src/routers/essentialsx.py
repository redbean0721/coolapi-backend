from fastapi import Depends, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from src.utils.auth import verify_api_key, permission_check

router = APIRouter()

class EssentialsxPostItem(BaseModel):
    key: str
    message: str

class WebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = WebSocketManager()

@router.post("/essentialsx", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
async def essentialsx(data: EssentialsxPostItem):
    if not verify_api_key(data.key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not permission_check(data.key, "essentials_post"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    await manager.broadcast(data.message)
    return JSONResponse(content={"message": f"Message '{data.message}' sent to WebSocket"})


@router.websocket("/essentials")
async def websocket_endpoint(websocket: WebSocket):
    api_key = websocket.query_params.get('key')
    if not api_key or not verify_api_key(api_key):
        await websocket.close(code=1008)
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not permission_check(api_key, "essentials_websocket"):
        await websocket.close(code=1008)
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 在這裡處理 WebSocket 接收到的訊息，例如傳遞給 Minecraft 插件
            print(f"Received message from WebSocket: {data}")
            # print(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
