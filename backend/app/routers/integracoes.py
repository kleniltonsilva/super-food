"""
Router de Integrações com Marketplaces (iFood, Open Delivery).
Modelo SaaS: credenciais na plataforma (Super Admin), restaurante apenas autoriza.

Fluxo iFood: connect → gera userCode → restaurante digita no portal → polling → authorized
Fluxo Open Delivery: connect → gera URL autorização → restaurante clica → webhook confirma
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from database import models
from ..database import get_db
from .. import auth
from ..feature_guard import verificar_feature

def get_rest(current_restaurante=Depends(verificar_feature("integracoes_marketplace"))):
    return current_restaurante

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/painel/integracoes", tags=["Integrações Marketplace"])


# ─── Listar marketplaces disponíveis + status do restaurante ────────────
@router.get("")
def listar_integracoes(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Lista marketplaces disponíveis (com credencial configurada pelo Super Admin) + status do restaurante."""
    # Buscar credenciais da plataforma ativas
    creds = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.ativo == True,
    ).all()

    # Buscar integrações do restaurante
    integracoes = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
    ).all()
    integ_map = {i.marketplace: i for i in integracoes}

    result = []
    for cred in creds:
        integ = integ_map.get(cred.marketplace)
        result.append({
            "marketplace": cred.marketplace,
            "disponivel": True,
            "conectado": integ.authorization_status == 'authorized' if integ else False,
            "ativo": integ.ativo if integ else False,
            "authorization_status": integ.authorization_status if integ else None,
            "merchant_id": integ.merchant_id if integ else None,
            "authorized_at": integ.authorized_at.isoformat() if integ and integ.authorized_at else None,
            "token_expires_at": integ.token_expires_at.isoformat() if integ and integ.token_expires_at else None,
        })

    return result


# ─── iFood: Iniciar fluxo de autorização (gera userCode) ────────────
@router.post("/ifood/connect")
async def connect_ifood(
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Iniciar fluxo de autorização iFood via userCode.
    Retorna um código que o restaurante deve digitar no Portal do Parceiro iFood.
    """
    # Verificar se a plataforma tem credenciais iFood
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == "ifood",
        models.CredencialPlataforma.ativo == True,
    ).first()
    if not cred:
        raise HTTPException(400, "iFood não está disponível. Contate o administrador da plataforma.")

    # Verificar se já está autorizado
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if integ and integ.authorization_status == 'authorized':
        raise HTTPException(400, "Restaurante já está conectado ao iFood. Desconecte primeiro para reconectar.")

    # Gerar userCode via API iFood
    from ..integrations.ifood.client import IFoodClient
    client = IFoodClient(
        integracao_id=integ.id if integ else 0,
        restaurante_id=rest.id,
        config={
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
        },
    )

    try:
        await client.start()
        user_code_data = await client.generate_user_code()
        await client.stop()
    except Exception as e:
        await client.stop()
        raise HTTPException(500, f"Erro ao gerar código de autorização: {str(e)}")

    if not user_code_data:
        raise HTTPException(500, "Falha ao gerar código de autorização iFood")

    # Criar ou atualizar integração com status pending
    if not integ:
        integ = models.IntegracaoMarketplace(
            restaurante_id=rest.id,
            marketplace="ifood",
            ativo=False,
            authorization_status='pending',
            config_json={
                "user_code": user_code_data.get("userCode"),
                "verification_url": user_code_data.get("verificationUrl"),
                "verification_url_complete": user_code_data.get("verificationUrlComplete"),
                "authorization_code_verifier": user_code_data.get("authorizationCodeVerifier"),
                "expires_in": user_code_data.get("expiresIn", 600),
            },
        )
        db.add(integ)
    else:
        integ.authorization_status = 'pending'
        integ.config_json = {
            **(integ.config_json or {}),
            "user_code": user_code_data.get("userCode"),
            "verification_url": user_code_data.get("verificationUrl"),
            "verification_url_complete": user_code_data.get("verificationUrlComplete"),
            "authorization_code_verifier": user_code_data.get("authorizationCodeVerifier"),
            "expires_in": user_code_data.get("expiresIn", 600),
        }

    db.commit()
    db.refresh(integ)

    return {
        "user_code": user_code_data.get("userCode"),
        "verification_url": user_code_data.get("verificationUrlComplete") or user_code_data.get("verificationUrl"),
        "expires_in": user_code_data.get("expiresIn", 600),
        "mensagem": "Digite este código no Portal do Parceiro iFood para autorizar.",
    }


# ─── iFood: Verificar status de autorização (polling frontend) ────────────
@router.get("/ifood/auth-status")
async def ifood_auth_status(
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Verifica se o restaurante já autorizou via userCode no iFood.
    O frontend faz polling neste endpoint até receber authorized=true.
    """
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        return {"status": "not_found", "authorized": False}

    if integ.authorization_status == 'authorized':
        return {"status": "authorized", "authorized": True, "merchant_id": integ.merchant_id}

    if integ.authorization_status != 'pending':
        return {"status": integ.authorization_status, "authorized": False}

    # Tentar verificar autorização via API iFood
    config = integ.config_json or {}
    authorization_code_verifier = config.get("authorization_code_verifier")
    user_code = config.get("user_code")

    if not authorization_code_verifier or not user_code:
        return {"status": "pending", "authorized": False, "mensagem": "Código expirado. Gere um novo."}

    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == "ifood",
        models.CredencialPlataforma.ativo == True,
    ).first()
    if not cred:
        return {"status": "error", "authorized": False, "mensagem": "Credenciais da plataforma não disponíveis"}

    from ..integrations.ifood.client import IFoodClient
    client = IFoodClient(
        integracao_id=integ.id,
        restaurante_id=rest.id,
        config={
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
        },
    )

    try:
        await client.start()
        token_data = await client.exchange_authorization_code(
            user_code=user_code,
            authorization_code_verifier=authorization_code_verifier,
        )
        await client.stop()
    except Exception as e:
        await client.stop()
        logger.debug(f"Autorização iFood pendente para rest {rest.id}: {e}")
        return {"status": "pending", "authorized": False}

    if token_data:
        # Autorização concedida!
        integ.authorization_status = 'authorized'
        integ.authorized_at = datetime.utcnow()
        integ.access_token = token_data.get("accessToken")
        integ.refresh_token = token_data.get("refreshToken")
        if token_data.get("expiresIn"):
            from datetime import timedelta
            integ.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expiresIn"])
        if token_data.get("merchantId"):
            integ.merchant_id = token_data["merchantId"]
        integ.ativo = True
        db.commit()

        return {
            "status": "authorized",
            "authorized": True,
            "merchant_id": integ.merchant_id,
            "mensagem": "Autorização concedida! iFood conectado com sucesso.",
        }

    return {"status": "pending", "authorized": False}


# ─── iFood: Desconectar ────────────
@router.post("/ifood/disconnect")
async def disconnect_ifood(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Desconectar restaurante do iFood (revogar autorização)."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == "ifood",
    ).first()

    if not integ:
        raise HTTPException(404, "Integração iFood não encontrada")

    integ.ativo = False
    integ.authorization_status = 'revoked'
    integ.access_token = None
    integ.refresh_token = None
    integ.token_expires_at = None
    db.commit()

    return {"mensagem": "iFood desconectado. Pedidos do iFood não serão mais recebidos."}


# ─── iFood: Status ────────────
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
    from datetime import timedelta
    hoje_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    pedidos_hoje = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.marketplace_source == "ifood",
        models.Pedido.data_criacao >= hoje_inicio,
    ).count()

    # Verificar polling ativo
    integration_manager = getattr(request.app.state, 'integration_manager', None)
    polling_ativo = False
    if integration_manager:
        client = integration_manager.get_client("ifood", rest.id)
        polling_ativo = client is not None and client.is_running

    return {
        "configurado": True,
        "ativo": integ.ativo,
        "authorization_status": integ.authorization_status,
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


# ─── Toggle ativo/inativo (qualquer marketplace) ────────────
@router.put("/{marketplace}/toggle")
async def toggle_integracao(
    marketplace: str,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Ativar/desativar integração (mantém autorização)."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if not integ:
        raise HTTPException(404, f"Integração {marketplace} não encontrada")

    if integ.authorization_status != 'authorized':
        raise HTTPException(400, "Conecte ao marketplace primeiro antes de ativar")

    integ.ativo = not integ.ativo
    db.commit()

    return {
        "ativo": integ.ativo,
        "mensagem": f"{marketplace} {'ativado' if integ.ativo else 'desativado'}. "
                    f"{'O polling será iniciado em até 30s.' if integ.ativo else ''}",
    }


# ─── Catalog Sync (iFood) ────────────
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
        raise HTTPException(400, "Token iFood não disponível. Reconecte ao iFood.")

    from ..integrations.ifood.catalog_sync import sync_catalog_to_ifood
    result = await sync_catalog_to_ifood(
        db=db,
        restaurante_id=rest.id,
        merchant_id=integ.merchant_id,
        access_token=integ.access_token,
    )

    return result


# ─── iFood: Test Order (para lojas de teste) ────────────
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

    ws_manager = getattr(request.app.state, 'ws_manager', None)
    if ws_manager:
        await ws_manager.broadcast({
            "tipo": "novo_pedido",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
        }, rest.id)

    return {"success": True, "order_id": order_id, "pedido_id": pedido.id, "comanda": comanda, "mensagem": "Pedido de teste criado (fallback)"}


# ─── Open Delivery: Conectar marketplace ────────────
@router.post("/{marketplace}/connect")
async def connect_opendelivery(
    marketplace: str,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Conectar restaurante a um marketplace Open Delivery (99food, keeta)."""
    if marketplace == "rappi":
        raise HTTPException(400, "Rappi usa API proprietária e ainda não é suportado. Em breve!")
    if marketplace not in ("99food", "keeta"):
        raise HTTPException(400, "Marketplace não suportado. Use: 99food, keeta")

    # Verificar credencial da plataforma
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == marketplace,
        models.CredencialPlataforma.ativo == True,
    ).first()
    if not cred:
        raise HTTPException(400, f"{marketplace} não está disponível. Contate o administrador da plataforma.")

    # Verificar se já está conectado
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if integ and integ.authorization_status == 'authorized':
        raise HTTPException(400, f"Já conectado ao {marketplace}. Desconecte primeiro.")

    webhook_url = f"https://superfood-api.fly.dev/webhooks/opendelivery/{rest.id}"

    # Criar ou atualizar integração com status pending
    if not integ:
        integ = models.IntegracaoMarketplace(
            restaurante_id=rest.id,
            marketplace=marketplace,
            ativo=False,
            authorization_status='pending',
            config_json={"webhook_url": webhook_url},
        )
        db.add(integ)
    else:
        integ.authorization_status = 'pending'
        integ.config_json = {**(integ.config_json or {}), "webhook_url": webhook_url}

    db.commit()
    db.refresh(integ)

    return {
        "marketplace": marketplace,
        "webhook_url": webhook_url,
        "mensagem": f"Configure o webhook no painel do {marketplace}: {webhook_url}. "
                    f"Quando o marketplace enviar o evento de autorização, a conexão será confirmada automaticamente.",
    }


# ─── Desconectar qualquer marketplace ────────────
@router.post("/{marketplace}/disconnect")
async def disconnect_marketplace(
    marketplace: str,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(get_db),
):
    """Desconectar restaurante de qualquer marketplace."""
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == rest.id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    if not integ:
        raise HTTPException(404, f"Integração {marketplace} não encontrada")

    integ.ativo = False
    integ.authorization_status = 'revoked'
    integ.access_token = None
    integ.refresh_token = None
    integ.token_expires_at = None
    db.commit()

    return {"mensagem": f"{marketplace} desconectado com sucesso"}


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

    # Identificar marketplace
    marketplace = payload.get("marketplace") or payload.get("source")
    if not marketplace:
        integracoes = db.query(models.IntegracaoMarketplace).filter(
            models.IntegracaoMarketplace.restaurante_id == restaurante_id,
            models.IntegracaoMarketplace.marketplace.in_(["99food", "rappi", "keeta"]),
        ).all()
        if len(integracoes) == 1:
            marketplace = integracoes[0].marketplace
        else:
            marketplace = "opendelivery"

    # Verificar assinatura HMAC (header X-App-Signature, chave = client_secret da plataforma)
    integ = db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.restaurante_id == restaurante_id,
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).first()

    cred_plat = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == marketplace,
        models.CredencialPlataforma.ativo == True,
    ).first()

    signature = request.headers.get("X-App-Signature", "")
    if cred_plat and cred_plat.client_secret:
        if not signature:
            raise HTTPException(401, "Assinatura do webhook obrigatoria")
        from ..integrations.opendelivery.client import OpenDeliveryClient
        if not OpenDeliveryClient.verify_webhook_signature(body, signature, cred_plat.client_secret):
            raise HTTPException(401, "Assinatura do webhook invalida")

    # Evento de autorização — confirmar conexão do restaurante
    event_type = payload.get("type") or payload.get("event_type") or payload.get("code", "")
    if event_type in ("AUTHORIZED", "MERCHANT_AUTHORIZED", "authorization"):
        if integ and integ.authorization_status == 'pending':
            integ.authorization_status = 'authorized'
            integ.authorized_at = datetime.utcnow()
            integ.ativo = True
            # Extrair merchantId do payload ou headers
            merchant_id = (
                payload.get("merchantId")
                or payload.get("merchant_id")
                or request.headers.get("X-App-MerchantId")
            )
            if merchant_id:
                integ.merchant_id = merchant_id
            db.commit()
            logger.info(f"Restaurante {restaurante_id} autorizado no {marketplace} via webhook")
        from fastapi.responses import Response
        return Response(status_code=200)

    # Evento normal — encaminhar para integration manager
    event = {
        "id": payload.get("id") or payload.get("eventId") or payload.get("event_id", ""),
        "type": event_type,
        "order": payload.get("order") or payload.get("data") or payload,
        "orderId": (
            payload.get("orderId")
            or payload.get("order_id")
            or (payload.get("order", {}) or {}).get("id", "")
        ),
        "marketplace": marketplace,
    }

    integration_manager = getattr(request.app.state, 'integration_manager', None)
    if integration_manager:
        client = integration_manager.get_client(marketplace, restaurante_id)
        if client and hasattr(client, 'receive_webhook_event'):
            client.receive_webhook_event(event)

    from fastapi.responses import Response
    return Response(status_code=200)
