from fastapi import FastAPI
from fastapi.websockets import WebSocket, WebSocketDisconnect
from .routers import restaurantes, pedidos
from .database import engine, Base
from typing import List, Dict
import json

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Super Restaurante API - SaaS Multi-Tenant")

app.include_router(restaurantes.router)
app.include_router(pedidos.router)

# Gerencia conexões WebSocket por restaurante_id
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, restaurante_id: int):
        await websocket.accept()
        if restaurante_id not in self.active_connections:
            self.active_connections[restaurante_id] = []
        self.active_connections[restaurante_id].append(websocket)

    def disconnect(self, websocket: WebSocket, restaurante_id: int):
        if restaurante_id in self.active_connections:
            self.active_connections[restaurante_id].remove(websocket)

    async def broadcast(self, message: dict, restaurante_id: int):
        if restaurante_id in self.active_connections:
            for connection in self.active_connections[restaurante_id][:]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    self.active_connections[restaurante_id].remove(connection)

manager = ConnectionManager()

@app.websocket("/ws/{restaurante_id}")
async def websocket_endpoint(websocket: WebSocket, restaurante_id: int):
    await manager.connect(websocket, restaurante_id)
    try:
        while True:
            data = await websocket.receive_text()  # Pode receber GPS do motoboy aqui
            # Exemplo: {"type": "gps", "lat": -23.55, "lon": -46.63}
            await manager.broadcast(json.loads(data), restaurante_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurante_id)

@app.get("/")
def root():
    return {"mensagem": "API Super Restaurante - WebSocket realtime ativo"}