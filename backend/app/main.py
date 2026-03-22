from fastapi import FastAPI, Query, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import os, json, time, uuid, logging, asyncio
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from .sentry_config import init_sentry

# Inicializa Sentry ANTES de qualquer import do app (captura erros de inicialização)
init_sentry()

from .routers import restaurantes, pedidos, site_cliente, carrinho, gps, auth_cliente, auth_restaurante, auth_motoboy, auth_admin, upload, painel
from .routers import motoboy as motoboy_router
from .routers import admin as admin_router
from .routers.integracoes import router as integracoes_router, webhook_router
from .routers import billing as billing_router
from .routers import billing_admin as billing_admin_router
from .routers import billing_webhooks as billing_webhooks_router
from .routers import pix as pix_router
from .routers import pix_webhooks as pix_webhooks_router
from .routers import auth_cozinheiro as auth_cozinheiro_router
from .routers import kds as kds_router
from .billing.billing_tasks import verificar_billing_periodico
from .pix.pix_tasks import verificar_pix_periodico
from .integrations.manager import integration_manager
from .database import engine, Base, get_db, SessionLocal
from . import models
from .logging_config import setup_logging
from .metrics import metrics
from .websocket_manager import create_manager
from .rate_limit import RateLimitMiddleware
from .middleware import DomainTenantMiddleware
from .demo_autopilot import demo_autopilot_loop

# Configura logging
setup_logging()
logger = logging.getLogger("superfood")

# WebSocket Managers (com suporte Redis Pub/Sub)
manager = create_manager(channel_prefix="ws:restaurante")
printer_manager = create_manager(channel_prefix="ws:printer")
kds_manager = create_manager(channel_prefix="ws:kds")


async def verificar_entregas_atrasadas(ws_manager):
    """Task periódica: verifica entregas atrasadas a cada 60s e broadcast alerta"""
    from datetime import datetime, timedelta
    while True:
        await asyncio.sleep(60)
        try:
            db = SessionLocal()
            try:
                agora = datetime.utcnow()
                # Busca entregas em rota
                entregas = db.query(models.Entrega).filter(
                    models.Entrega.status == "em_rota"
                ).all()

                for entrega in entregas:
                    pedido = db.query(models.Pedido).filter(
                        models.Pedido.id == entrega.pedido_id
                    ).first()
                    if not pedido:
                        continue

                    # Tolerância do restaurante
                    config = db.query(models.ConfigRestaurante).filter(
                        models.ConfigRestaurante.restaurante_id == pedido.restaurante_id
                    ).first()
                    tolerancia = (config.tolerancia_atraso_min if config and hasattr(config, 'tolerancia_atraso_min') and config.tolerancia_atraso_min else 10)

                    # Tempo estimado
                    tempo_estimado = entrega.tempo_entrega
                    if not tempo_estimado and entrega.distancia_km:
                        tempo_estimado = round((entrega.distancia_km / 25) * 60)
                    if not tempo_estimado:
                        tempo_estimado = 30  # fallback 30 min

                    # Referência de início
                    referencia = entrega.delivery_started_at or entrega.atribuido_em or pedido.data_criacao
                    if not referencia:
                        continue

                    decorrido = round((agora - referencia).total_seconds() / 60)

                    if decorrido > (tempo_estimado + tolerancia):
                        await ws_manager.broadcast({
                            "tipo": "entrega_atrasada",
                            "dados": {
                                "pedido_id": pedido.id,
                                "comanda": pedido.comanda,
                                "motoboy_id": entrega.motoboy_id,
                                "tempo_estimado_min": tempo_estimado,
                                "tempo_decorrido_min": decorrido,
                            }
                        }, pedido.restaurante_id)
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Verificação entregas atrasadas: {e}")


_entrega_task = None
_billing_task = None
_pix_task = None
_demo_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown da aplicacao"""
    global _entrega_task, _billing_task, _pix_task, _demo_task
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

    logger.info("Derekh Food API iniciada")

    # Inicia WebSocket managers (Redis Pub/Sub se disponivel)
    if hasattr(manager, 'start'):
        await manager.start()
    if hasattr(printer_manager, 'start'):
        await printer_manager.start()
    if hasattr(kds_manager, 'start'):
        await kds_manager.start()

    # Inicia verificação periódica de entregas atrasadas
    _entrega_task = asyncio.create_task(verificar_entregas_atrasadas(manager))

    # Inicia task periódica de billing
    _billing_task = asyncio.create_task(verificar_billing_periodico(manager))

    # Inicia task periódica de Pix (saque automático)
    _pix_task = asyncio.create_task(verificar_pix_periodico())

    # Inicia demo autopilot (progride pedidos demo automaticamente)
    _demo_task = asyncio.create_task(demo_autopilot_loop(manager))

    # Inicia integration manager (polling marketplaces)
    integration_manager.set_app(app)
    await integration_manager.start()

    yield

    # Shutdown
    if _entrega_task:
        _entrega_task.cancel()
        try:
            await _entrega_task
        except asyncio.CancelledError:
            pass
    if _billing_task:
        _billing_task.cancel()
        try:
            await _billing_task
        except asyncio.CancelledError:
            pass
    if _pix_task:
        _pix_task.cancel()
        try:
            await _pix_task
        except asyncio.CancelledError:
            pass
    if _demo_task:
        _demo_task.cancel()
        try:
            await _demo_task
        except asyncio.CancelledError:
            pass
    if hasattr(manager, 'stop'):
        await manager.stop()
    if hasattr(printer_manager, 'stop'):
        await printer_manager.stop()
    if hasattr(kds_manager, 'stop'):
        await kds_manager.stop()
    await integration_manager.stop()
    logger.info("Derekh Food API encerrada")


app = FastAPI(
    title="Derekh Food API - SaaS Multi-Tenant",
    version="4.0.0",
    lifespan=lifespan,
)

# Expor WebSocket managers e integration manager no app.state
app.state.ws_manager = manager
app.state.printer_manager = printer_manager
app.state.kds_manager = kds_manager
app.state.integration_manager = integration_manager

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
app.include_router(integracoes_router)
app.include_router(webhook_router)
app.include_router(billing_router.router)
app.include_router(billing_admin_router.router)
app.include_router(billing_webhooks_router.router)
app.include_router(pix_router.router)
app.include_router(pix_webhooks_router.router)
app.include_router(auth_cozinheiro_router.router)
app.include_router(kds_router.router)

# ==================== Endpoint público — Planos (landing page) ====================
@app.get("/api/public/planos")
def planos_publicos(db: Session = Depends(get_db)):
    """Retorna planos para a landing page pública. Sem autenticação."""
    try:
        planos_db = db.query(models.Plano).filter(
            models.Plano.ativo == True
        ).order_by(models.Plano.ordem).all()
        config = db.query(models.ConfigBilling).first()
        desconto_anual = config.desconto_anual_percentual if config else 20.0
    except Exception:
        # Fallback se tabela não existir ainda
        return JSONResponse(content=[
            {"nome": "Básico", "valor": 169.90, "limite_motoboys": 2, "descricao": "Ideal para começar", "destaque": False, "ordem": 1},
            {"nome": "Essencial", "valor": 279.90, "limite_motoboys": 5, "descricao": "Para restaurantes em crescimento", "destaque": False, "ordem": 2},
            {"nome": "Avançado", "valor": 329.90, "limite_motoboys": 10, "descricao": "Para operações maiores", "destaque": True, "ordem": 3},
            {"nome": "Premium", "valor": 527.00, "limite_motoboys": 999, "descricao": "Sem limites", "destaque": False, "ordem": 4},
        ])

    if not planos_db:
        return JSONResponse(content=[])

    return [
        {
            "nome": p.nome,
            "valor": p.valor,
            "limite_motoboys": p.limite_motoboys,
            "descricao": p.descricao,
            "destaque": p.destaque,
            "ordem": p.ordem,
            "desconto_anual": desconto_anual,
        }
        for p in planos_db
    ]


# ==================== Endpoint público — Restaurantes Demo ====================
@app.get("/api/public/demos")
def demos_publicos(db: Session = Depends(get_db)):
    """Retorna restaurantes demo para a landing page. Sem autenticação."""
    try:
        demos = db.query(models.Restaurante).filter(
            models.Restaurante.email.like("%@superfood.test"),
            models.Restaurante.ativo == True,
        ).all()

        result = []
        for r in demos:
            site_config = db.query(models.SiteConfig).filter(
                models.SiteConfig.restaurante_id == r.id
            ).first()
            result.append({
                "codigo_acesso": r.codigo_acesso,
                "nome_fantasia": r.nome_fantasia,
                "tipo_restaurante": site_config.tipo_restaurante if site_config else "restaurante",
                "cor_primaria": site_config.tema_cor_primaria if site_config else "#EA580C",
            })
        return result
    except Exception:
        return JSONResponse(content=[])


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
    # Notifica admin se printer agent está conectado
    if printer_manager.has_connections(restaurante_id):
        await manager.broadcast({"tipo": "printer_status", "dados": {"online": True}}, restaurante_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Encaminhar reimprimir_pedido para printer_manager
            if isinstance(msg, dict) and msg.get("tipo") == "reimprimir_pedido":
                await printer_manager.broadcast(msg, restaurante_id)
            else:
                await manager.broadcast(msg, restaurante_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurante_id)


@app.websocket("/ws/printer/{restaurante_id}")
async def websocket_printer(websocket: WebSocket, restaurante_id: int, token: Optional[str] = Query(None)):
    """WebSocket para printer agent — auth via JWT na query string"""
    from jose import JWTError, jwt as jose_jwt
    from .auth import SECRET_KEY, ALGORITHM

    # Validar JWT
    if not token:
        await websocket.close(code=4001, reason="Token obrigatorio")
        return
    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        sub = int(payload.get("sub"))
        role = payload.get("role")
        if role != "restaurante" or sub != restaurante_id:
            await websocket.close(code=4003, reason="Acesso negado")
            return
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001, reason="Token invalido")
        return

    await printer_manager.connect(websocket, restaurante_id)
    # Notifica admin WS que impressora conectou
    await manager.broadcast({"tipo": "printer_status", "dados": {"online": True}}, restaurante_id)
    logger.info(f"Printer agent conectado: restaurante={restaurante_id}")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            tipo = msg.get("tipo") if isinstance(msg, dict) else None
            if tipo == "print_ack":
                # Repassa status de impressão para o admin WS
                await manager.broadcast(msg, restaurante_id)
            elif tipo == "status":
                # Agent informando status (impressoras disponíveis, etc)
                await manager.broadcast({"tipo": "printer_status", "dados": msg.get("dados", {})}, restaurante_id)
    except WebSocketDisconnect:
        printer_manager.disconnect(websocket, restaurante_id)
        await manager.broadcast({"tipo": "printer_status", "dados": {"online": False}}, restaurante_id)
        logger.info(f"Printer agent desconectado: restaurante={restaurante_id}")

# ==================== WebSocket KDS ====================
@app.websocket("/ws/kds/{restaurante_id}")
async def websocket_kds(websocket: WebSocket, restaurante_id: int, token: Optional[str] = Query(None)):
    """WebSocket para KDS — auth via JWT na query string, role=cozinheiro"""
    from jose import JWTError, jwt as jose_jwt
    from .auth import SECRET_KEY, ALGORITHM

    if not token:
        await websocket.close(code=4001, reason="Token obrigatorio")
        return
    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        role = payload.get("role")
        rest_id = payload.get("restaurante_id")
        if role != "cozinheiro" or rest_id != restaurante_id:
            await websocket.close(code=4003, reason="Acesso negado")
            return
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001, reason="Token invalido")
        return

    await kds_manager.connect(websocket, restaurante_id)
    logger.info(f"KDS conectado: restaurante={restaurante_id}")

    try:
        while True:
            data = await websocket.receive_text()
            # KDS pode enviar pings ou acks
    except WebSocketDisconnect:
        kds_manager.disconnect(websocket, restaurante_id)
        logger.info(f"KDS desconectado: restaurante={restaurante_id}")


# ==================== SPA React (KDS / Cozinha) ====================
@app.get("/cozinha", response_class=HTMLResponse)
async def serve_cozinha_root():
    """Serve o app KDS React PWA"""
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)


@app.get("/cozinha/{path:path}", response_class=HTMLResponse)
async def serve_cozinha_catchall(path: str):
    """Catch-all para SPA routing do app cozinha"""
    asset_response = _serve_react_asset(path)
    if asset_response:
        return asset_response
    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h1>Build do React não encontrado</h1>", status_code=500)


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


# ==================== Domínio personalizado → Site restaurante ====================
def _serve_tenant_site(restaurante_id: int):
    """Serve o site do cliente para um domínio personalizado"""
    db = SessionLocal()
    try:
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.id == restaurante_id
        ).first()
        if not restaurante:
            raise HTTPException(status_code=404, detail="Restaurante não encontrado")
        codigo = restaurante.codigo_acesso
    finally:
        db.close()

    index_file = REACT_BUILD_DIR / "index.html"
    if index_file.exists():
        content = index_file.read_text()
        script = f'<script>window.RESTAURANTE_CODIGO="{codigo}";</script>'
        content = content.replace('</head>', f'{script}</head>')
        return HTMLResponse(content=content)

    return HTMLResponse("<h1>Build não encontrado</h1>", status_code=500)


@app.get("/", response_class=HTMLResponse)
async def serve_root(request: Request):
    """Rota raiz — se domínio personalizado, serve site do restaurante. Senão, landing page."""
    domain_tenant_id = getattr(request.state, "domain_tenant_id", None)
    if domain_tenant_id:
        return _serve_tenant_site(domain_tenant_id)
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_catchall(request: Request, path: str):
    """Catch-all — se domínio personalizado, serve SPA do restaurante"""
    domain_tenant_id = getattr(request.state, "domain_tenant_id", None)
    if not domain_tenant_id:
        raise HTTPException(status_code=404)

    # Se é um asset estático, serve o arquivo
    asset_response = _serve_react_asset(path)
    if asset_response:
        return asset_response

    # Senão, serve o SPA com codigo_acesso injetado
    return _serve_tenant_site(domain_tenant_id)
