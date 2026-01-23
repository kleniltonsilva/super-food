from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .routers import restaurantes, pedidos, site_cliente, carrinho
from .database import engine, Base, get_db
from . import models
from typing import List, Dict
import json

# Cria tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Super Food API - SaaS Multi-Tenant")

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Templates
templates = Jinja2Templates(directory="backend/templates")

# Routers API
app.include_router(restaurantes.router)
app.include_router(pedidos.router)
app.include_router(site_cliente.router)
app.include_router(carrinho.router)

# ==================== ROTAS HTML (SITE DO CLIENTE) ====================

@app.get("/site/{codigo_acesso}", response_class=HTMLResponse)
async def site_home(
    request: Request,
    codigo_acesso: str,
    db: Session = Depends(get_db)
):
    """Página inicial do site do cliente"""

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        return templates.TemplateResponse("erro_404.html", {"request": request})

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()

    if not site_config or not site_config.site_ativo:
        return templates.TemplateResponse("site_indisponivel.html", {"request": request})

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()

    produtos_destaque = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante.id,
        models.Produto.destaque == True,
        models.Produto.disponivel == True
    ).limit(8).all()

    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante.id,
        models.CategoriaMenu.ativo == True
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    return templates.TemplateResponse("site/home.html", {
        "request": request,
        "restaurante": restaurante,
        "site_config": site_config,
        "config": config,
        "produtos_destaque": produtos_destaque,
        "categorias": categorias,
        "show_whatsapp": True,
        "meta_description": site_config.meta_description or f"Peça delivery online em {restaurante.nome_fantasia}",
        "meta_keywords": site_config.meta_keywords or "delivery, comida, pedido online"
    })


@app.get("/site/{codigo_acesso}/cardapio", response_class=HTMLResponse)
async def site_cardapio(
    request: Request,
    codigo_acesso: str,
    db: Session = Depends(get_db)
):
    """Página do cardápio"""

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        return templates.TemplateResponse("erro_404.html", {"request": request})

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()

    produtos = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante.id,
        models.Produto.disponivel == True
    ).order_by(
        models.Produto.destaque.desc(),
        models.Produto.ordem_exibicao,
        models.Produto.nome
    ).all()

    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante.id,
        models.CategoriaMenu.ativo == True
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    return templates.TemplateResponse("site/cardapio.html", {
        "request": request,
        "restaurante": restaurante,
        "site_config": site_config,
        "config": config,
        "produtos": produtos,
        "categorias": categorias,
        "show_whatsapp": False
    })


# ==================== WEBSOCKET ====================

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


@app.get("/")
def root():
    return {"mensagem": "Super Food API - Site do Cliente ativo!"}
