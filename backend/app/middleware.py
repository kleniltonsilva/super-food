# backend/app/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy.orm import Session
from .database import SessionLocal
from .auth import get_current_restaurante
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware que injeta automaticamente tenant_id em todas as queries do SQLAlchemy.
    Garante isolamento de dados entre restaurantes.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Rotas públicas que não precisam de tenant_id
        public_paths = ["/", "/docs", "/openapi.json", "/restaurantes/signup", "/restaurantes/login"]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Extrai tenant_id do token JWT (se autenticado)
        tenant_id = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            try:
                db = SessionLocal()
                try:
                    restaurante = get_current_restaurante(auth_header.split(" ")[1], db)
                    tenant_id = restaurante.id
                    request.state.tenant_id = tenant_id
                    logger.info(f"🔐 Tenant {tenant_id} autenticado em {request.url.path}")
                finally:
                    db.close()
            except HTTPException:
                pass  # Token inválido, continua sem tenant_id
        
        response = await call_next(request)
        return response

def get_tenant_id(request: Request) -> int:
    """
    Extrai tenant_id da request. Usado em dependencias FastAPI.
    """
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao necessaria para acessar este recurso"
        )
    return request.state.tenant_id


class DomainTenantMiddleware(BaseHTTPMiddleware):
    """
    Resolve restaurante por dominio customizado ou subdominio *.superfood.com.br
    Seta request.state.domain_tenant_id para uso nos endpoints do site
    """

    # Rotas que nao precisam de resolucao por dominio
    BYPASS_PREFIXES = (
        "/api/", "/painel/", "/admin/", "/auth/", "/health",
        "/metrics", "/ws/", "/static/", "/docs", "/openapi.json",
        "/superadmin", "/entregador",
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Bypass rotas internas
        if any(path.startswith(prefix) for prefix in self.BYPASS_PREFIXES):
            return await call_next(request)

        host = request.headers.get("host", "").split(":")[0].lower()

        # Ignora localhost e IPs
        if host in ("localhost", "127.0.0.1", "") or host.replace(".", "").isdigit():
            return await call_next(request)

        # Tenta resolver por dominio customizado ou subdominio
        tenant_id = self._resolve_tenant(host)
        if tenant_id:
            request.state.domain_tenant_id = tenant_id

        return await call_next(request)

    def _resolve_tenant(self, host: str):
        """Resolve host para restaurante_id"""
        from . import models

        db = SessionLocal()
        try:
            # 1. Dominio personalizado (ex: pedidos.minhapizzaria.com.br)
            dominio = db.query(models.DominioPersonalizado).filter(
                models.DominioPersonalizado.dominio == host,
                models.DominioPersonalizado.verificado == True,
                models.DominioPersonalizado.ativo == True,
            ).first()
            if dominio:
                return dominio.restaurante_id

            # 2. Subdominio *.superfood.com.br
            if host.endswith(".superfood.com.br"):
                subdomain = host.replace(".superfood.com.br", "")
                restaurante = db.query(models.Restaurante).filter(
                    models.Restaurante.codigo_acesso == subdomain.upper(),
                    models.Restaurante.ativo == True,
                ).first()
                if restaurante:
                    return restaurante.id

            return None
        except Exception as e:
            logger.warning(f"Erro ao resolver dominio {host}: {e}")
            return None
        finally:
            db.close()