from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import os, json, time, uuid, logging
from typing import List, Dict
from contextlib import asynccontextmanager

from .routers import restaurantes, pedidos, site_cliente, carrinho, gps, auth_cliente, auth_restaurante, auth_motoboy, auth_admin, upload, painel
from .routers import motoboy as motoboy_router
from .routers import admin as admin_router
from .database import engine, Base, get_db
from . import models
from .logging_config import setup_logging
from .metrics import metrics
from .websocket_manager import create_manager
from .rate_limit import RateLimitMiddleware
from .middleware import DomainTenantMiddleware

# Configura logging
setup_logging()
logger = logging.getLogger("superfood")

# WebSocket Manager (com suporte Redis Pub/Sub)
manager = create_manager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown da aplicacao"""
    # Startup
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        # Em producao, Alembic roda antes do gunicorn (via CMD no Dockerfile)
        logger.info("Producao: tabelas gerenciadas pelo Alembic")
    else:
        Base.metadata.create_all(bind=engine)

    # Cria super admin padrao se nao existir
    try:
        from database.session import criar_super_admin_padrao
        criar_super_admin_padrao()
    except Exception as e:
        logger.warning(f"Seed super admin: {e}")

    logger.info("Super Food API iniciada")

    # Inicia WebSocket manager (Redis Pub/Sub se disponivel)
    if hasattr(manager, 'start'):
        await manager.start()

    yield

    # Shutdown
    if hasattr(manager, 'stop'):
        await manager.stop()
    logger.info("Super Food API encerrada")


app = FastAPI(
    title="Super Food API - SaaS Multi-Tenant",
    version="4.0.0",
    lifespan=lifespan,
)

# Expor WebSocket manager no app.state para uso nos routers
app.state.ws_manager = manager

# ==================== Middlewares ====================
# Ordem importa: ultimo adicionado = primeiro executado

# Rate Limiting (via Redis, gracioso sem Redis)
app.add_middleware(RateLimitMiddleware)

# Dominio personalizado → restaurante_id
app.add_middleware(DomainTenantMiddleware)

# Gzip (min 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS
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


# ==================== Request Logging Middleware ====================
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Loga cada request com timing e request_id"""
    # Ignora health checks do log
    path = request.url.path
    if path in ("/health/live", "/health/ready"):
        return await call_next(request)

    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Registra metricas
    metrics.record_request(response.status_code, duration_ms)

    # Log (apenas requests lentos ou erros em producao)
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production" and response.status_code < 400 and duration_ms < 500:
        pass  # Ignora requests normais em producao
    else:
        logger.info(
            f"{request.method} {path} {response.status_code} {duration_ms}ms",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

    response.headers["X-Request-ID"] = request_id
    return response

# Diretório do React build
REACT_BUILD_DIR = Path(__file__).parent.parent.parent / "restaurante-pedido-online" / "dist" / "public"

# ==================== Static files ====================
# Static do backend
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Assets do React build (JS, CSS, imagens, temas, PWA)
if REACT_BUILD_DIR.exists():
    if (REACT_BUILD_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(REACT_BUILD_DIR / "assets")), name="react-assets")
    if (REACT_BUILD_DIR / "themes").exists():
        app.mount("/themes", StaticFiles(directory=str(REACT_BUILD_DIR / "themes")), name="react-themes")
    if (REACT_BUILD_DIR / "icons").exists():
        app.mount("/icons", StaticFiles(directory=str(REACT_BUILD_DIR / "icons")), name="react-icons")

# Templates Jinja2
templates = Jinja2Templates(directory="backend/templates")

# ==================== Routers API (ANTES do SPA mount) ====================
app.include_router(restaurantes.router)
app.include_router(pedidos.router)
app.include_router(site_cliente.router)
app.include_router(carrinho.router)
app.include_router(gps.router)
app.include_router(auth_cliente.router)
app.include_router(upload.router)
app.include_router(auth_restaurante.router)
app.include_router(auth_motoboy.router)
app.include_router(auth_admin.router)
app.include_router(motoboy_router.router)
app.include_router(admin_router.router)
app.include_router(painel.router)

# ==================== PWA files (manifest, service worker) ====================
@app.get("/manifest.json")
async def serve_manifest():
    """Serve manifest.json do PWA"""
    manifest_file = REACT_BUILD_DIR / "manifest.json"
    if manifest_file.exists():
        from fastapi.responses import Response
        return Response(content=manifest_file.read_bytes(), media_type="application/manifest+json")
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.get("/sw.js")
async def serve_sw():
    """Serve service worker do PWA"""
    sw_file = REACT_BUILD_DIR / "sw.js"
    if sw_file.exists():
        from fastapi.responses import Response
        return Response(content=sw_file.read_bytes(), media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# ==================== Health Check Endpoints ====================
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check completo — verifica API, banco e Redis"""
    checks = {"api": "ok"}

    # Check banco de dados
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Check Redis (opcional)
    try:
        from .cache import get_redis
        r = get_redis()
        if r:
            r.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"

    status = "healthy" if checks["database"] == "ok" else "degraded"
    status_code = 200 if status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": "4.0.0",
            "checks": checks,
        },
    )


@app.get("/health/live")
async def health_live():
    """Liveness probe — API esta rodando?"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready(db: Session = Depends(get_db)):
    """Readiness probe — API esta pronta para receber trafego?"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


# ==================== Metrics Endpoint ====================
@app.get("/metrics")
async def get_metrics(
    current_admin: models.SuperAdmin = Depends(
        lambda: None  # Placeholder — proteger em producao
    ),
):
    """Metricas de performance (proteger com auth em producao)"""
    return metrics.get_metrics()


# ==================== WebSocket ====================
@app.websocket("/ws/{restaurante_id}")
async def websocket_endpoint(websocket: WebSocket, restaurante_id: int):
    await manager.connect(websocket, restaurante_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(json.loads(data), restaurante_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurante_id)

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
    return HTMLResponse("<h1>Build do React não encontrado. Execute: cd restaurante-pedido-online && npm run build</h1>", status_code=500)


@app.get("/cliente/{codigo_acesso}/{path:path}", response_class=HTMLResponse)
async def serve_react_app_catchall(codigo_acesso: str, path: str):
    """Catch-all para SPA routing — redireciona tudo para index.html"""
    # Verifica se é um asset (js, css, imagens)
    if path.startswith("assets/") or "." in path.split("/")[-1]:
        asset_file = REACT_BUILD_DIR / path
        if asset_file.exists():
            import mimetypes
            content_type = mimetypes.guess_type(str(asset_file))[0] or "application/octet-stream"
            from fastapi.responses import Response
            return Response(content=asset_file.read_bytes(), media_type=content_type)

    # Para rotas do SPA, serve o index.html
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        content = index_file.read_text()
        script = f'<script>window.RESTAURANTE_CODIGO="{codigo_acesso}";</script>'
        content = content.replace('</head>', f'{script}</head>')
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)


# ==================== SPA React (painel admin) ====================
def _serve_react_asset(path: str):
    """Serve asset estático do build React. Retorna None se não encontrado."""
    from fastapi.responses import Response
    import mimetypes
    asset_file = REACT_BUILD_DIR / path
    if asset_file.exists() and asset_file.is_file():
        content_type = mimetypes.guess_type(str(asset_file))[0] or "application/octet-stream"
        return Response(content=asset_file.read_bytes(), media_type=content_type)
    return None


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_root():
    """Serve o painel admin React"""
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado. Execute: cd restaurante-pedido-online && npm run build</h1>", status_code=500)


@app.get("/admin/{path:path}", response_class=HTMLResponse)
async def serve_admin_catchall(path: str):
    """Catch-all para SPA routing do admin"""
    # Tenta servir asset estático primeiro
    asset_response = _serve_react_asset(path)
    if asset_response:
        return asset_response

    # Para rotas do SPA, serve o index.html
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)


# ==================== SPA React (app motoboy/entregador) ====================
@app.get("/entregador", response_class=HTMLResponse)
async def serve_entregador_root():
    """Serve o app motoboy React PWA"""
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado. Execute: cd restaurante-pedido-online && npm run build</h1>", status_code=500)


@app.get("/entregador/{path:path}", response_class=HTMLResponse)
async def serve_entregador_catchall(path: str):
    """Catch-all para SPA routing do app entregador"""
    # Tenta servir asset estático primeiro
    asset_response = _serve_react_asset(path)
    if asset_response:
        return asset_response

    # Para rotas do SPA, serve o index.html
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)


# ==================== SPA React (super admin) ====================
@app.get("/superadmin", response_class=HTMLResponse)
async def serve_superadmin_root():
    """Serve o painel super admin React"""
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado. Execute: cd restaurante-pedido-online && npm run build</h1>", status_code=500)


@app.get("/superadmin/{path:path}", response_class=HTMLResponse)
async def serve_superadmin_catchall(path: str):
    """Catch-all para SPA routing do super admin"""
    asset_response = _serve_react_asset(path)
    if asset_response:
        return asset_response
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)
