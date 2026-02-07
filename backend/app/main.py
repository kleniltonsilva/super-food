from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import os, json
from typing import List, Dict

from .routers import restaurantes, pedidos, site_cliente, carrinho, gps
from .database import engine, Base, get_db
from . import models

# Cria tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Super Food API - SaaS Multi-Tenant")

# ==================== CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:8504",  # Streamlit
        "http://localhost:3000",  # React dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretório do React build
REACT_BUILD_DIR = Path(__file__).parent.parent.parent / "restaurante-pedido-online" / "dist"

# ==================== Static files ====================
# Static do backend
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Assets e SPA React
if REACT_BUILD_DIR.exists():
    # Monta toda a pasta do build como raiz
    app.mount("/", StaticFiles(directory=str(REACT_BUILD_DIR), html=True), name="react_spa")

# Templates Jinja2
templates = Jinja2Templates(directory="backend/templates")

# ==================== Routers API ====================
app.include_router(restaurantes.router)
app.include_router(pedidos.router)
app.include_router(site_cliente.router)
app.include_router(carrinho.router)
app.include_router(gps.router)

# ==================== WebSocket ====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, restaurante_id: int):
        await websocket.accept()
        self.active_connections.setdefault(restaurante_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, restaurante_id: int):
        if restaurante_id in self.active_connections:
            self.active_connections[restaurante_id].remove(websocket)

    async def broadcast(self, message: dict, restaurante_id: int):
        for connection in self.active_connections.get(restaurante_id, []):
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
            data = await websocket.receive_text()
            await manager.broadcast(json.loads(data), restaurante_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurante_id)

# ==================== Rotas HTML existentes ====================
@app.get("/site/{codigo_acesso}", response_class=HTMLResponse)
async def site_home(request: Request, codigo_acesso: str, db: Session = Depends(get_db)):
    # mantém todo o código original do site Jinja2
    ...

@app.get("/site/{codigo_acesso}/cardapio", response_class=HTMLResponse)
async def site_cardapio(request: Request, codigo_acesso: str, db: Session = Depends(get_db)):
    # mantém todo o código original do cardápio
    ...

# ==================== SPA React (cliente) ====================
@app.get("/cliente/{codigo_acesso}", response_class=HTMLResponse)
async def serve_react_app(codigo_acesso: str):
    """Serve o React SPA e injeta o código do restaurante"""
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        content = index_file.read_text()
        script = f'<script>window.RESTAURANTE_CODIGO="{codigo_acesso}";</script>'
        content = content.replace('</head>', f'{script}</head>')
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)

