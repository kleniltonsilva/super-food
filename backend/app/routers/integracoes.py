"""
Router de Integrações com Marketplaces (iFood, Open Delivery).
Endpoints para setup, status, webhook e catalog sync.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from database import models
from ..database import get_db
from .. import auth

def get_rest(current_restaurante=Depends(auth.get_current_restaurante)):
    return current_restaurante

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/painel/integracoes", tags=["Integrações Marketplace"])


# ─── Schemas ────────────────────────────────
class IFoodSetupRequest(BaseModel):
    client_id: str
    client_secret: str
    merchant_id: str


class OpenDeliverySetupRequest(BaseModel):
    marketplace: str  # 99food, rappi, keeta
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    merchant_id: Optional[str] = None
    api_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None


# ─── Listar integrações ────────────────────────────
@router.get("")
def listar_integracoes(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Lista todas as integrações do restaurante."""
    integracoes = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
    ).all()

    result = []
    for integ in integracoes:
        result.append({
            "id": integ.id,
            "marketplace": integ.marketplace,
            "ativo": integ.ativo,
            "merchant_id": integ.merchant_id,
            "has_credentials": bool(integ.client_id and integ.client_secret),
            "token_expires_at": integ.token_expires_at.isoformat() if integ.token_expires_at else None,
            "criado_em": integ.criado_em.isoformat() if integ.criado_em else None,
            "atualizado_em": integ.atualizado_em.isoformat() if integ.atualizado_em else None,
        })

    return result


# ─── iFood Setup ────────────────────────────
@router.post("/ifood/setup")
async def setup_ifood(
    dados: IFoodSetupRequest,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Configurar integração com iFood."""
    # Verificar se já existe
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if integ:
        integ.client_id = dados.client_id
        integ.client_secret = dados.client_secret
        integ.merchant_id = dados.merchant_id
    else:
        integ = models.IntegracaoMarketplace(
            restaurante_id=rest.id,
            marketplace="ifood",
            client_id=dados.client_id,
            client_secret=dados.client_secret,
            merchant_id=dados.merchant_id,
            ativo=False,
        )
        db.add(integ)

    db.commit()
    db.refresh(integ)

    return {
        "id": integ.id,
        "marketplace": "ifood",
        "merchant_id": integ.merchant_id,
        "ativo": integ.ativo,
        "mensagem": "Credenciais iFood salvas. Use /test para testar a conexão.",
    }


@router.post("/ifood/test")
async def test_ifood(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Testar conexão com iFood (verifica OAuth2)."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        raise HTTPException(404, "Integração iFood não configurada")

    from ..integrations.ifood.client import IFoodClient
    client = IFoodClient(
        integracao_id=integ.id,
        restaurante_id=rest.id,
        config={
            "client_id": integ.client_id,
            "client_secret": integ.client_secret,
            "merchant_id": integ.merchant_id,
        },
    )

    try:
        await client.start()
        auth_ok = await client.authenticate()
        await client.stop()

        if auth_ok:
            return {"success": True, "mensagem": "Conexão com iFood OK! Credenciais válidas."}
        else:
            return {"success": False, "mensagem": "Falha na autenticação. Verifique client_id e client_secret."}
    except Exception as e:
        await client.stop()
        return {"success": False, "mensagem": f"Erro ao conectar: {str(e)}"}


@router.put("/ifood/toggle")
async def toggle_ifood(
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Ativar/desativar integração iFood."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        raise HTTPException(404, "Integração iFood não configurada")

    if not integ.client_id or not integ.client_secret:
        raise HTTPException(400, "Configure as credenciais antes de ativar")

    integ.ativo = not integ.ativo
    db.commit()

    return {
        "ativo": integ.ativo,
        "mensagem": f"iFood {'ativado' if integ.ativo else 'desativado'}. "
                    f"{'O polling de pedidos será iniciado em até 30 segundos.' if integ.ativo else ''}",
    }


@router.delete("/ifood")
async def remover_ifood(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Remover integração iFood."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        raise HTTPException(404, "Integração iFood não encontrada")

    db.delete(integ)
    db.commit()

    return {"mensagem": "Integração iFood removida"}


@router.get("/ifood/status")
async def status_ifood(
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Status detalhado da integração iFood."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        return {"configurado": False}

    # Último evento processado
    ultimo_evento = db.query(models.MarketplaceEventLog).filter(
        models.MarketplaceEventLog.restaurante_id == rest.id,
        models.MarketplaceEventLog.marketplace == "ifood",
    ).order_by(models.MarketplaceEventLog.criado_em.desc()).first()

    # Pedidos marketplace hoje
    from datetime import datetime, timedelta
    hoje_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    pedidos_hoje = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.marketplace_source == "ifood",
        models.Pedido.data_criacao >= hoje_inicio,
    ).count()

    # Verificar se o manager tem o client ativo
    integration_manager = getattr(request.app.state, 'integration_manager', None)
    polling_ativo = False
    if integration_manager:
        client = integration_manager.get_client("ifood", rest.id)
        polling_ativo = client is not None and client.is_running

    return {
        "configurado": True,
        "ativo": integ.ativo,
        "merchant_id": integ.merchant_id,
        "token_valido": integ.token_expires_at > datetime.utcnow() if integ.token_expires_at else False,
        "token_expira_em": integ.token_expires_at.isoformat() if integ.token_expires_at else None,
        "polling_ativo": polling_ativo,
        "ultimo_evento": {
            "tipo": ultimo_evento.event_type,
            "data": ultimo_evento.criado_em.isoformat(),
            "processado": ultimo_evento.processed,
        } if ultimo_evento else None,
        "pedidos_hoje": pedidos_hoje,
    }


# ─── Catalog Sync (iFood) ────────────────────────────
@router.post("/ifood/catalog-sync")
async def sync_catalog_ifood(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Sincronizar cardápio do restaurante com o catálogo iFood."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ or not integ.ativo:
        raise HTTPException(400, "Integração iFood não está ativa")

    if not integ.access_token:
        raise HTTPException(400, "Token iFood não disponível. Teste a conexão primeiro.")

    from ..integrations.ifood.catalog_sync import sync_catalog_to_ifood
    result = await sync_catalog_to_ifood(
        db=db,
        restaurante_id=rest.id,
        merchant_id=integ.merchant_id,
        access_token=integ.access_token,
    )

    return result


# ─── Open Delivery Setup ────────────────────────────
@router.post("/ifood/test-order")
async def test_order_ifood(
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Gerar pedido de teste simulando iFood (apenas para lojas de teste)."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()
    if not integ or not integ.ativo:
        raise HTTPException(400, "Integração iFood não está ativa")

    import uuid
    from datetime import datetime
    order_id = f"test-{uuid.uuid4().hex[:12]}"
    fake_event = {
        "id": f"evt-{uuid.uuid4().hex[:8]}",
        "code": "PLACED",
        "orderId": order_id,
        "order": {
            "id": order_id,
            "displayId": f"TST-{uuid.uuid4().hex[:4].upper()}",
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "type": "DELIVERY",
            "merchant": {"id": integ.merchant_id, "name": rest.nome},
            "customer": {
                "name": "Cliente Teste iFood",
                "phone": {"number": "41999998888"},
            },
            "items": [
                {
                    "id": "test-item-1",
                    "name": "Pizza Margherita Grande",
                    "quantity": 1,
                    "unitPrice": 42.90,
                    "totalPrice": 42.90,
                    "subItems": [
                        {"name": "Borda Recheada Catupiry", "quantity": 1, "unitPrice": 8.00, "totalPrice": 8.00}
                    ],
                    "observations": "Sem cebola",
                },
                {
                    "id": "test-item-2",
                    "name": "Coca-Cola 2L",
                    "quantity": 2,
                    "unitPrice": 12.00,
                    "totalPrice": 24.00,
                    "subItems": [],
                    "observations": "",
                },
            ],
            "payments": {
                "methods": [{"method": "CREDIT", "type": "ONLINE", "value": 79.90}]
            },
            "total": {
                "subTotal": 74.90,
                "deliveryFee": 5.00,
                "benefits": 0,
                "orderAmount": 79.90,
            },
            "deliveryAddress": {
                "streetName": "Rua Brasil",
                "streetNumber": "234",
                "neighborhood": "Centro",
                "city": "Curitiba",
                "state": "PR",
                "postalCode": "80000-000",
                "complement": "Apto 12",
                "reference": "Próximo à praça",
                "coordinates": {"latitude": -25.4284, "longitude": -49.2733},
            },
        },
    }

    # Processar diretamente pelo manager
    integration_manager = getattr(request.app.state, 'integration_manager', None)
    if integration_manager:
        client = integration_manager.get_client("ifood", rest.id)
        if client:
            await integration_manager._process_events(client, [fake_event])
            return {"success": True, "order_id": order_id, "mensagem": "Pedido de teste criado com sucesso"}

    # Fallback: processar inline se manager não disponível
    from ..integrations.ifood.mapper import ifood_order_to_pedido
    from .painel import _gerar_proxima_comanda
    pedido_data = ifood_order_to_pedido(fake_event["order"], rest.id)
    comanda = _gerar_proxima_comanda(db, rest.id)

    pedido = models.Pedido(
        restaurante_id=rest.id,
        comanda=comanda,
        tipo=pedido_data.get("tipo", "delivery"),
        origem="marketplace",
        tipo_entrega=pedido_data.get("tipo_entrega", "entrega"),
        cliente_nome=pedido_data.get("cliente_nome", "Cliente Teste iFood"),
        cliente_telefone=pedido_data.get("cliente_telefone"),
        endereco_entrega=pedido_data.get("endereco_entrega"),
        latitude_entrega=pedido_data.get("latitude_entrega"),
        longitude_entrega=pedido_data.get("longitude_entrega"),
        itens=pedido_data.get("itens_texto", "Pedido teste iFood"),
        carrinho_json=pedido_data.get("carrinho_json", []),
        observacoes=pedido_data.get("observacoes"),
        valor_total=pedido_data.get("valor_total", 0),
        valor_subtotal=pedido_data.get("valor_subtotal", 0),
        valor_taxa_entrega=pedido_data.get("valor_taxa_entrega", 0),
        forma_pagamento=pedido_data.get("forma_pagamento"),
        status="pendente",
        marketplace_source="ifood",
        marketplace_order_id=order_id,
        marketplace_display_id=pedido_data.get("marketplace_display_id"),
        marketplace_raw_json=fake_event["order"],
    )
    db.add(pedido)
    db.commit()

    # Broadcast novo_pedido
    ws_manager = getattr(request.app.state, 'ws_manager', None)
    if ws_manager:
        await ws_manager.broadcast({
            "tipo": "novo_pedido",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
        }, rest.id)

    return {"success": True, "order_id": order_id, "pedido_id": pedido.id, "comanda": comanda, "mensagem": "Pedido de teste criado (fallback)"}


@router.post("/opendelivery/setup")
async def setup_opendelivery(
    dados: OpenDeliverySetupRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Configurar integração Open Delivery (99Food, Rappi, Keeta)."""
    if dados.marketplace not in ("99food", "rappi", "keeta"):
        raise HTTPException(400, "Marketplace não suportado. Use: 99food, rappi, keeta")

    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == dados.marketplace,
    ).first()

    config_json = {}
    if dados.api_base_url:
        config_json["api_base_url"] = dados.api_base_url
    if dados.webhook_secret:
        config_json["webhook_secret"] = dados.webhook_secret

    if integ:
        if dados.client_id:
            integ.client_id = dados.client_id
        if dados.client_secret:
            integ.client_secret = dados.client_secret
        if dados.merchant_id:
            integ.merchant_id = dados.merchant_id
        if config_json:
            integ.config_json = config_json
    else:
        integ = models.IntegracaoMarketplace(
            restaurante_id=rest.id,
            marketplace=dados.marketplace,
            client_id=dados.client_id,
            client_secret=dados.client_secret,
            merchant_id=dados.merchant_id,
            config_json=config_json,
            ativo=False,
        )
        db.add(integ)

    db.commit()
    db.refresh(integ)

    return {
        "id": integ.id,
        "marketplace": dados.marketplace,
        "ativo": integ.ativo,
        "webhook_url": f"/webhooks/opendelivery/{rest.id}",
        "mensagem": f"Integração {dados.marketplace} configurada. "
                    f"Configure o webhook no painel do marketplace: "
                    f"https://superfood-api.fly.dev/webhooks/opendelivery/{rest.id}",
    }


@router.put("/opendelivery/{marketplace}/toggle")
async def toggle_opendelivery(
    marketplace: str,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Ativar/desativar integração Open Delivery."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if not integ:
        raise HTTPException(404, f"Integração {marketplace} não encontrada")

    integ.ativo = not integ.ativo
    db.commit()

    return {"ativo": integ.ativo, "mensagem": f"{marketplace} {'ativado' if integ.ativo else 'desativado'}"}


@router.delete("/opendelivery/{marketplace}")
async def remover_opendelivery(
    marketplace: str,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Remover integração Open Delivery."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if not integ:
        raise HTTPException(404, f"Integração {marketplace} não encontrada")

    db.delete(integ)
    db.commit()

    return {"mensagem": f"Integração {marketplace} removida"}


# ─── Webhook Open Delivery (SEM auth JWT — marketplace envia diretamente) ────
webhook_router = APIRouter(tags=["Webhooks Marketplace"])


@webhook_router.post("/webhooks/opendelivery/{restaurante_id}")
async def webhook_opendelivery(
    restaurante_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Endpoint webhook para receber eventos de marketplaces Open Delivery.
    Este endpoint NÃO requer autenticação JWT — é chamado diretamente pelo marketplace.
    """
    # Verificar se restaurante existe
    rest = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id,
        models.Restaurante.ativo == True,
    ).first()
    if not rest:
        raise HTTPException(404, "Restaurante não encontrado")

    body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Payload JSON inválido")

    # Identificar qual marketplace está enviando
    # (Pode vir no header, no payload, ou inferido da integração ativa)
    marketplace = payload.get("marketplace") or payload.get("source")
    if not marketplace:
        # Tentar inferir pela integração ativa
        integracoes = db.query(models.IntegracaoMarketplace).filter(
            models.IntegracaoMarketplace.restaurante_id == restaurante_id,
            models.IntegracaoMarketplace.ativo == True,
            models.IntegracaoMarketplace.marketplace.in_(["99food", "rappi", "keeta"]),
        ).all()
        if len(integracoes) == 1:
            marketplace = integracoes[0].marketplace
        else:
            marketplace = "opendelivery"

    # Verificar assinatura HMAC (se configurado)
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == restaurante_id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if integ and integ.config_json and integ.config_json.get("webhook_secret"):
        from ..integrations.opendelivery.client import OpenDeliveryClient
        signature = request.headers.get("X-Webhook-Signature", "")
        if not OpenDeliveryClient.verify_webhook_signature(body, signature, integ.config_json["webhook_secret"]):
            raise HTTPException(401, "Assinatura do webhook inválida")

    # Construir evento normalizado
    event = {
        "id": payload.get("id") or payload.get("eventId") or payload.get("event_id", ""),
        "type": payload.get("type") or payload.get("event_type") or payload.get("code", "newOrder"),
        "order": payload.get("order") or payload.get("data") or payload,
        "orderId": (
            payload.get("orderId")
            or payload.get("order_id")
            or (payload.get("order", {}) or {}).get("id", "")
        ),
        "marketplace": marketplace,
    }

    # Encaminhar para o integration manager
    integration_manager = getattr(request.app.state, 'integration_manager', None)
    if integration_manager:
        client = integration_manager.get_client(marketplace, restaurante_id)
        if client and hasattr(client, 'receive_webhook_event'):
            client.receive_webhook_event(event)

    # Sempre retornar 200 para o marketplace não reenviar
    return JSONResponse(status_code=200, content={"status": "received"})
