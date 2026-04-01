"""
Router Bot WhatsApp Humanoide — Webhook Evolution + Endpoints Admin + Super Admin.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import sqlalchemy as sa
from sqlalchemy import func, case, cast, Date
from datetime import datetime, timedelta
from typing import Optional
import logging
import hmac
import os

from .. import models, database
from ..auth import get_current_restaurante, get_current_admin
from ..feature_guard import verificar_feature

logger = logging.getLogger("superfood.bot.router")

EVOLUTION_WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET", "")
if not EVOLUTION_WEBHOOK_SECRET:
    logger.warning("EVOLUTION_WEBHOOK_SECRET não configurado — webhook sem validação em dev")

# Campos que o Super Admin pode alterar via PUT /api/admin/bot/instancia/{id}
ADMIN_BOT_CAMPOS_PERMITIDOS = {
    "bot_ativo", "nome_atendente", "tom_personalidade", "voz_tts", "idioma",
    "whatsapp_numero", "whatsapp_provider",
    "evolution_instance", "evolution_api_url", "evolution_api_key",
    "meta_phone_number_id", "meta_access_token", "meta_waba_id", "meta_app_secret", "meta_webhook_verify_token",
    "pode_criar_pedido", "pode_alterar_pedido", "pode_cancelar_pedido",
    "pode_dar_desconto", "desconto_maximo_pct",
    "pode_reembolsar", "reembolso_maximo_valor",
    "pode_receber_pix", "pode_agendar",
    "comportamento_fechado", "estoque_esgotado_acao",
    "cancelamento_ate_status", "taxa_cancelamento",
    "avaliacao_ativa", "delay_avaliacao_min", "reclamacao_acao", "reclamacao_credito_pct",
    "repescagem_ativa", "repescagem_dias_inativo", "repescagem_desconto_pct", "repescagem_usar_frequencia",
    "impressao_automatica_bot", "stt_ativo", "tts_autonomo", "tts_provider",
    "max_tokens_dia",
    "politica_atraso", "politica_pedido_errado", "politica_item_faltando", "politica_qualidade",
    "google_maps_url", "avaliacao_perguntar_problemas", "avaliacao_pedir_google_review",
    "avaliacao_lembrete_24h", "desconto_por_review", "desconto_review_pct",
}

router = APIRouter(tags=["Bot WhatsApp"])


# ==================== WEBHOOK EVOLUTION API (público) ====================

@router.post("/webhooks/evolution")
async def webhook_evolution(request: Request):
    """Webhook público da Evolution API. Responde 200 imediatamente e processa em background."""
    # Validar apikey header (Evolution envia em cada webhook)
    if EVOLUTION_WEBHOOK_SECRET:
        apikey = request.headers.get("apikey", "")
        if not hmac.compare_digest(apikey, EVOLUTION_WEBHOOK_SECRET):
            return JSONResponse(status_code=401, content={"error": "unauthorized"})

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "ok"})

    from ..bot.atendente import processar_webhook
    resultado = await processar_webhook(payload)

    return JSONResponse({"status": "ok", **resultado})


# ==================== WEBHOOK META CLOUD API (público) ====================

META_APP_SECRET = os.getenv("META_APP_SECRET", "")

@router.get("/webhooks/meta-whatsapp")
async def webhook_meta_verify(request: Request):
    """Verificação de webhook Meta (challenge/response).
    Verifica token contra BotConfig (provider=meta) e BotMetaGateway (legado)."""
    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")

    if not mode or not token or not challenge:
        return JSONResponse(status_code=400, content={"error": "missing params"})

    from ..bot.meta_cloud_client import verificar_webhook

    db = database.SessionLocal()
    try:
        # 1. Verificar BotConfig com provider='meta' (nova arquitetura)
        meta_configs = db.query(models.BotConfig).filter(
            models.BotConfig.whatsapp_provider == "meta",
            models.BotConfig.bot_ativo == True,
            models.BotConfig.meta_webhook_verify_token.isnot(None),
        ).all()
        for cfg in meta_configs:
            result = verificar_webhook(mode, token, challenge, cfg.meta_webhook_verify_token)
            if result:
                return JSONResponse(content=int(result), media_type="text/plain")

        # 2. Verificar BotMetaGateway (legado — redirect mode)
        gateways = db.query(models.BotMetaGateway).filter(
            models.BotMetaGateway.ativo == True,
        ).all()
        for gw in gateways:
            result = verificar_webhook(mode, token, challenge, gw.webhook_verify_token)
            if result:
                return JSONResponse(content=int(result), media_type="text/plain")
    finally:
        db.close()

    return JSONResponse(status_code=403, content={"error": "verification failed"})


@router.post("/webhooks/meta-whatsapp")
async def webhook_meta_receive(request: Request):
    """Recebe mensagens via Meta Cloud API.
    Identifica restaurante por phone_number_id:
    - Se BotConfig com provider='meta' → processa como humanoide (IA responde)
    - Se BotMetaGateway → redirect para número ativo (legado)
    """
    body = await request.body()

    # Validar assinatura HMAC-SHA256 (busca app_secret do BotConfig ou env)
    sig = request.headers.get("X-Hub-Signature-256", "")
    if sig:
        # Tentar validar contra BotConfigs Meta
        assinatura_valida = False
        db_check = database.SessionLocal()
        try:
            meta_configs = db_check.query(models.BotConfig).filter(
                models.BotConfig.whatsapp_provider == "meta",
                models.BotConfig.meta_app_secret.isnot(None),
            ).all()
            from ..bot.meta_cloud_client import validar_webhook_signature
            for cfg in meta_configs:
                if validar_webhook_signature(body, sig, cfg.meta_app_secret):
                    assinatura_valida = True
                    break
            # Fallback: env var global
            if not assinatura_valida and META_APP_SECRET:
                assinatura_valida = validar_webhook_signature(body, sig, META_APP_SECRET)
        finally:
            db_check.close()

        if not assinatura_valida:
            return JSONResponse(status_code=401, content={"error": "invalid signature"})
    elif META_APP_SECRET:
        # Sem header de assinatura mas APP_SECRET configurado → rejeitar em prod
        logger.warning("Meta webhook sem X-Hub-Signature-256")

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "ok"})

    # Determinar modo: humanoide (BotConfig meta) ou redirect (BotMetaGateway legado)
    import asyncio
    phone_number_id = _extrair_phone_number_id(payload)

    if phone_number_id:
        db_route = database.SessionLocal()
        try:
            # Verificar se é humanoide (BotConfig com provider='meta')
            bot_meta = db_route.query(models.BotConfig).filter(
                models.BotConfig.meta_phone_number_id == phone_number_id,
                models.BotConfig.whatsapp_provider == "meta",
                models.BotConfig.bot_ativo == True,
            ).first()

            if bot_meta:
                # Processar como humanoide IA
                from ..bot.atendente import processar_webhook_meta
                asyncio.create_task(processar_webhook_meta(payload))
                return JSONResponse({"status": "ok"})
        finally:
            db_route.close()

    # Fallback: redirect via BotMetaGateway (legado)
    asyncio.create_task(_processar_meta_webhook_legado(payload))
    return JSONResponse({"status": "ok"})


def _extrair_phone_number_id(payload: dict) -> Optional[str]:
    """Extrai phone_number_id do payload Meta webhook."""
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            pid = metadata.get("phone_number_id")
            if pid:
                return pid
    return None


async def _processar_meta_webhook_legado(payload: dict):
    """Processa webhook Meta legado: identifica restaurante via BotMetaGateway → responde com redirect."""
    try:
        entry = payload.get("entry", [])
        if not entry:
            return

        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                if value.get("messaging_product") != "whatsapp":
                    continue

                messages = value.get("messages", [])
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id", "")

                if not phone_number_id or not messages:
                    continue

                db = database.SessionLocal()
                try:
                    gateway = db.query(models.BotMetaGateway).filter(
                        models.BotMetaGateway.phone_number_id == phone_number_id,
                        models.BotMetaGateway.ativo == True,
                    ).first()

                    if not gateway:
                        logger.debug(f"Meta webhook legado: gateway não encontrado para {phone_number_id}")
                        continue

                    rest_id = gateway.restaurante_id

                    restaurante = db.query(models.Restaurante).filter(
                        models.Restaurante.id == rest_id,
                    ).first()

                    from ..bot.phone_pool import get_active_number
                    pool_entry = get_active_number(db, rest_id)

                    bot_config = db.query(models.BotConfig).filter(
                        models.BotConfig.restaurante_id == rest_id,
                        models.BotConfig.bot_ativo == True,
                    ).first()

                    numero_ativo = None
                    if pool_entry:
                        numero_ativo = pool_entry.whatsapp_numero
                    elif bot_config:
                        numero_ativo = bot_config.whatsapp_numero

                    if not numero_ativo:
                        logger.warning(f"Meta webhook legado: nenhum número ativo para rest={rest_id}")
                        continue

                    nome_rest = restaurante.nome_fantasia if restaurante else "Restaurante"

                    from ..bot import meta_cloud_client
                    for msg in messages:
                        numero_cliente = msg.get("from", "")
                        if not numero_cliente:
                            continue

                        try:
                            await meta_cloud_client.enviar_redirect(
                                numero_cliente=numero_cliente,
                                phone_number_id=phone_number_id,
                                access_token=gateway.access_token,
                                nome_restaurante=nome_rest,
                                numero_ativo=numero_ativo,
                                template_name=gateway.template_redirect_nome or "redirect_atendimento",
                            )
                        except Exception as send_err:
                            logger.error(f"Meta redirect falhou para {numero_cliente[:8]}***: {send_err}")
                finally:
                    db.close()

    except Exception as e:
        logger.error(f"Erro processando Meta webhook legado: {e}", exc_info=True)


# ==================== ENDPOINTS PAINEL RESTAURANTE ====================

@router.get("/painel/bot/config")
def get_bot_config(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Retorna configuração do bot WhatsApp do restaurante."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if not config:
        return {"ativo": False, "configurado": False}

    return {
        "configurado": True,
        "bot_ativo": config.bot_ativo,
        "whatsapp_provider": getattr(config, "whatsapp_provider", "evolution") or "evolution",
        "nome_atendente": config.nome_atendente,
        "tom_personalidade": config.tom_personalidade,
        "voz_tts": config.voz_tts,
        "idioma": config.idioma,
        "whatsapp_numero": config.whatsapp_numero,
        "evolution_instance": config.evolution_instance,
        # Meta Cloud API (só visível se provider='meta')
        "meta_phone_number_id": getattr(config, "meta_phone_number_id", None),
        # Capacidades
        "pode_criar_pedido": config.pode_criar_pedido,
        "pode_alterar_pedido": config.pode_alterar_pedido,
        "pode_cancelar_pedido": config.pode_cancelar_pedido,
        "pode_dar_desconto": config.pode_dar_desconto,
        "desconto_maximo_pct": config.desconto_maximo_pct,
        "pode_reembolsar": config.pode_reembolsar,
        "reembolso_maximo_valor": config.reembolso_maximo_valor,
        "pode_receber_pix": config.pode_receber_pix,
        "pode_agendar": config.pode_agendar,
        # Comportamento
        "comportamento_fechado": config.comportamento_fechado,
        "estoque_esgotado_acao": config.estoque_esgotado_acao,
        "cancelamento_ate_status": config.cancelamento_ate_status,
        "taxa_cancelamento": config.taxa_cancelamento,
        # Pós-entrega
        "avaliacao_ativa": config.avaliacao_ativa,
        "delay_avaliacao_min": config.delay_avaliacao_min,
        "reclamacao_acao": config.reclamacao_acao,
        # Repescagem
        "repescagem_ativa": config.repescagem_ativa,
        "repescagem_dias_inativo": config.repescagem_dias_inativo,
        "repescagem_desconto_pct": config.repescagem_desconto_pct,
        "repescagem_usar_frequencia": config.repescagem_usar_frequencia,
        # Políticas de erro
        "politica_atraso": config.politica_atraso,
        "politica_pedido_errado": config.politica_pedido_errado,
        "politica_item_faltando": config.politica_item_faltando,
        "politica_qualidade": config.politica_qualidade,
        # Google Maps / Avaliação v2
        "google_maps_url": config.google_maps_url,
        "avaliacao_perguntar_problemas": config.avaliacao_perguntar_problemas,
        "avaliacao_pedir_google_review": config.avaliacao_pedir_google_review,
        # Impressão
        "impressao_automatica_bot": config.impressao_automatica_bot,
        # Audio
        "stt_ativo": config.stt_ativo,
        "tts_autonomo": config.tts_autonomo,
        # Limites
        "max_tokens_dia": config.max_tokens_dia,
        "tokens_usados_hoje": config.tokens_usados_hoje,
    }


@router.put("/painel/bot/config")
async def update_bot_config(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Atualiza configuração do bot WhatsApp (permissões, comportamento, etc.)."""
    body = await request.json()

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Bot não configurado. Solicite ativação pelo Super Admin.")

    # Campos atualizáveis pelo dono do restaurante
    campos_permitidos = [
        "nome_atendente", "tom_personalidade", "voz_tts",
        "pode_criar_pedido", "pode_alterar_pedido", "pode_cancelar_pedido",
        "pode_dar_desconto", "desconto_maximo_pct",
        "pode_reembolsar", "reembolso_maximo_valor",
        "pode_receber_pix", "pode_agendar",
        "comportamento_fechado", "estoque_esgotado_acao",
        "cancelamento_ate_status", "taxa_cancelamento",
        "avaliacao_ativa", "delay_avaliacao_min",
        "reclamacao_acao", "reclamacao_credito_pct",
        "repescagem_ativa", "repescagem_dias_inativo", "repescagem_desconto_pct",
        "repescagem_usar_frequencia",
        "impressao_automatica_bot",
        "stt_ativo", "tts_autonomo", "tts_provider",
        "politica_atraso", "politica_pedido_errado", "politica_item_faltando", "politica_qualidade",
        "google_maps_url", "avaliacao_perguntar_problemas", "avaliacao_pedir_google_review",
        "avaliacao_lembrete_24h", "desconto_por_review", "desconto_review_pct",
    ]

    for campo in campos_permitidos:
        if campo in body:
            setattr(config, campo, body[campo])

    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Configuração do bot atualizada"}


@router.post("/painel/bot/ativar")
def ativar_bot(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Ativa o bot WhatsApp (requer config prévia pelo Super Admin)."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="Bot não configurado. Solicite ativação pelo Super Admin.")

    provider = getattr(config, "whatsapp_provider", "") or "evolution"
    if provider == "meta":
        if not config.meta_phone_number_id or not config.meta_access_token:
            raise HTTPException(status_code=400, detail="Meta Cloud API não configurada. Contate o suporte.")
    else:
        if not config.evolution_instance or not config.evolution_api_url:
            raise HTTPException(status_code=400, detail="Instância Evolution não configurada. Contate o suporte.")

    config.bot_ativo = True
    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Bot WhatsApp ativado!"}


@router.post("/painel/bot/desativar")
def desativar_bot(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Desativa o bot WhatsApp."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if config:
        config.bot_ativo = False
        config.atualizado_em = datetime.utcnow()
        db.commit()

    return {"sucesso": True, "mensagem": "Bot WhatsApp desativado"}


# ==================== PHONE REGISTRATION (Self-Service Onboarding) ====================

META_ACCESS_TOKEN_GLOBAL = os.getenv("META_ACCESS_TOKEN", "")
META_WABA_ID_GLOBAL = os.getenv("META_WABA_ID", "1486557139857851")
META_APP_SECRET_GLOBAL = os.getenv("META_APP_SECRET", "")
META_WEBHOOK_VERIFY_TOKEN_GLOBAL = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")


def _get_or_create_bot_config(db: Session, restaurante_id: int) -> "models.BotConfig":
    """Retorna BotConfig existente ou cria um novo com defaults."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante_id
    ).first()
    if not config:
        config = models.BotConfig(restaurante_id=restaurante_id)
        db.add(config)
        db.flush()
    return config


@router.get("/painel/bot/phone/status")
def phone_status(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Retorna estado atual do registro de telefone e dados do perfil."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if not config:
        return {
            "registration_status": "none",
            "phone_number_id": None,
            "whatsapp_numero": None,
            "display_name": None,
            "about": None,
            "description": None,
            "profile_photo_url": None,
            "registered_at": None,
            "bot_ativo": False,
        }

    status = getattr(config, "phone_registration_status", None) or "none"

    # Se bot está ativo com Meta provider mas status é none/registered, marcar como active
    if config.bot_ativo and config.whatsapp_provider == "meta" and config.meta_phone_number_id:
        if status in ("none", "registered"):
            status = "active"

    return {
        "registration_status": status,
        "phone_number_id": config.meta_phone_number_id,
        "whatsapp_numero": config.whatsapp_numero,
        "display_name": getattr(config, "phone_display_name", None),
        "about": getattr(config, "phone_about", None),
        "description": getattr(config, "phone_description", None),
        "profile_photo_url": getattr(config, "phone_profile_photo_url", None),
        "registered_at": config.phone_registered_at.isoformat() if getattr(config, "phone_registered_at", None) else None,
        "bot_ativo": config.bot_ativo,
    }


@router.post("/painel/bot/phone/registrar")
async def phone_registrar(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Registra número de telefone na WABA e solicita código de verificação.

    NÃO usa feature guard — verifica tier manualmente e ativa add-on inline.
    Para Essencial/Avançado: ativa add-on automaticamente se necessário.
    Para Premium: incluso grátis.
    Para Básico: bloqueado (tier < 2).
    """
    body = await request.json()
    numero = (body.get("numero") or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    display_name = (body.get("display_name") or restaurante.nome_fantasia or "").strip()

    if not numero or len(numero) < 10:
        raise HTTPException(status_code=400, detail="Número de telefone inválido")
    if not display_name:
        raise HTTPException(status_code=400, detail="Nome de exibição é obrigatório")

    # Verificar tier mínimo (Básico bloqueado)
    from ..feature_flags import PlanTier, ADDON_INCLUDED_TIER, ADDON_MIN_TIER
    plano_map = {"basico": 1, "essencial": 2, "avancado": 3, "premium": 4}
    tier = plano_map.get((restaurante.plano or "basico").lower(), 1)

    min_tier = ADDON_MIN_TIER.get("bot_whatsapp", 2)
    if tier < min_tier:
        raise HTTPException(
            status_code=403,
            detail="WhatsApp Humanoide disponível a partir do plano Essencial.",
        )

    included_tier = ADDON_INCLUDED_TIER.get("bot_whatsapp", 4)
    if tier < included_tier:
        # Precisa do add-on — verificar se já está ativo
        addon_ativo = getattr(restaurante, "addon_bot_whatsapp", False)
        if not addon_ativo:
            # Ativar add-on via billing
            try:
                from ..billing.billing_service import ativar_addon_bot
                resultado = await ativar_addon_bot(restaurante.id, db)
                logger.info(f"Add-on bot_whatsapp ativado para restaurante {restaurante.id}: {resultado}")
            except Exception as e:
                logger.error(f"Erro ao ativar add-on bot_whatsapp: {e}")
                raise HTTPException(
                    status_code=402,
                    detail=f"Erro ao ativar add-on WhatsApp Humanoide: {e}"
                )

    # Registrar número na WABA
    from ..bot.meta_phone_manager import registrar_numero, solicitar_codigo, MetaApiError

    try:
        result = await registrar_numero(numero, display_name)
        phone_number_id = result["phone_number_id"]
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao registrar número: {e.message}")

    # Criar/atualizar BotConfig
    config = _get_or_create_bot_config(db, restaurante.id)
    config.whatsapp_numero = numero
    config.whatsapp_provider = "meta"
    config.meta_phone_number_id = phone_number_id
    config.meta_access_token = META_ACCESS_TOKEN_GLOBAL
    config.meta_waba_id = META_WABA_ID_GLOBAL
    config.meta_app_secret = META_APP_SECRET_GLOBAL
    config.meta_webhook_verify_token = META_WEBHOOK_VERIFY_TOKEN_GLOBAL
    config.phone_registration_status = "pending_code"
    config.phone_display_name = display_name
    config.atualizado_em = datetime.utcnow()
    db.commit()

    # Solicitar código de verificação automaticamente
    try:
        await solicitar_codigo(phone_number_id, "SMS")
    except MetaApiError as e:
        logger.warning(f"Erro ao solicitar código SMS (número já verificado?): {e.message}")

    return {
        "sucesso": True,
        "phone_number_id": phone_number_id,
        "mensagem": f"Número registrado! Código de verificação enviado por SMS para {numero}.",
    }


@router.post("/painel/bot/phone/solicitar-codigo")
async def phone_solicitar_codigo(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Re-solicita código de verificação via SMS ou VOICE."""
    body = await request.json()
    metodo = (body.get("metodo") or "SMS").upper()
    if metodo not in ("SMS", "VOICE"):
        metodo = "SMS"

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()
    if not config or not config.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Número não registrado. Registre primeiro.")

    from ..bot.meta_phone_manager import solicitar_codigo, MetaApiError

    try:
        await solicitar_codigo(config.meta_phone_number_id, metodo)
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao solicitar código: {e.message}")

    return {"sucesso": True, "mensagem": f"Código enviado via {metodo}"}


@router.post("/painel/bot/phone/verificar-codigo")
async def phone_verificar_codigo(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Verifica código de 6 dígitos e registra na Cloud API."""
    body = await request.json()
    codigo = (body.get("codigo") or "").strip()

    if not codigo or len(codigo) != 6 or not codigo.isdigit():
        raise HTTPException(status_code=400, detail="Código deve ter 6 dígitos")

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()
    if not config or not config.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Número não registrado")

    from ..bot.meta_phone_manager import verificar_codigo, registrar_cloud_api, MetaApiError

    # Passo 1: Verificar código
    try:
        await verificar_codigo(config.meta_phone_number_id, codigo)
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Código inválido: {e.message}")

    # Passo 2: Registrar na Cloud API
    try:
        await registrar_cloud_api(config.meta_phone_number_id)
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao registrar na Cloud API: {e.message}")

    config.phone_registration_status = "registered"
    config.phone_registered_at = datetime.utcnow()
    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {
        "sucesso": True,
        "mensagem": "Número verificado e registrado na Cloud API!",
        "registration_status": "registered",
    }


@router.put("/painel/bot/phone/perfil")
async def phone_perfil(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Atualiza perfil do WhatsApp Business (about, description, display_name)."""
    body = await request.json()

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()
    if not config or not config.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Número não registrado")

    about = (body.get("about") or "").strip()
    description = (body.get("description") or "").strip()
    display_name = (body.get("display_name") or "").strip()
    nome_atendente = (body.get("nome_atendente") or "").strip()
    ativar = body.get("ativar", False)

    # Atualizar perfil na Meta API
    from ..bot.meta_phone_manager import atualizar_perfil, MetaApiError

    try:
        await atualizar_perfil(
            phone_number_id=config.meta_phone_number_id,
            about=about,
            description=description,
            vertical="RESTAURANT",
        )
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar perfil: {e.message}")

    # Salvar localmente
    if about:
        config.phone_about = about
    if description:
        config.phone_description = description
    if display_name:
        config.phone_display_name = display_name
    if nome_atendente:
        config.nome_atendente = nome_atendente

    # Se pediu para ativar, ligar o bot
    if ativar:
        config.bot_ativo = True
        config.phone_registration_status = "active"

    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {
        "sucesso": True,
        "mensagem": "Perfil atualizado" + (" e bot ativado!" if ativar else ""),
        "registration_status": config.phone_registration_status,
    }


@router.post("/painel/bot/phone/foto")
async def phone_foto(
    foto: UploadFile = File(...),
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Upload de foto de perfil do WhatsApp Business (JPG/PNG, max 5MB)."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()
    if not config or not config.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Número não registrado")

    # Validar tipo
    content_type = foto.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use JPG ou PNG.")

    # Ler e validar tamanho (max 5MB)
    image_bytes = await foto.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Imagem muito grande. Máximo 5MB.")

    from ..bot.meta_phone_manager import upload_foto_perfil, MetaApiError

    try:
        await upload_foto_perfil(config.meta_phone_number_id, image_bytes, content_type)
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao enviar foto: {e.message}")

    # Salvar URL placeholder (Meta não retorna URL pública — usamos marker)
    config.phone_profile_photo_url = f"meta://profile/{config.meta_phone_number_id}"
    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Foto de perfil atualizada"}


@router.post("/painel/bot/phone/trocar-numero")
async def phone_trocar_numero(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Troca o número de telefone: desvincula antigo e registra novo."""
    body = await request.json()
    numero_novo = (body.get("numero_novo") or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if not numero_novo or len(numero_novo) < 10:
        raise HTTPException(status_code=400, detail="Número novo inválido")

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()
    if not config or not config.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Nenhum número registrado para trocar")

    from ..bot.meta_phone_manager import desvincular_numero, registrar_numero, solicitar_codigo, MetaApiError

    old_phone_id = config.meta_phone_number_id

    # Desativar bot durante troca
    config.bot_ativo = False

    # Desvincular número antigo
    try:
        await desvincular_numero(old_phone_id)
    except MetaApiError as e:
        logger.warning(f"Erro ao desvincular número antigo {old_phone_id}: {e.message}")

    # Registrar novo número
    try:
        result = await registrar_numero(numero_novo, config.phone_display_name or restaurante.nome_fantasia)
        new_phone_id = result["phone_number_id"]
    except MetaApiError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao registrar novo número: {e.message}")

    # Atualizar config
    config.whatsapp_numero = numero_novo
    config.meta_phone_number_id = new_phone_id
    config.meta_access_token = META_ACCESS_TOKEN_GLOBAL
    config.phone_registration_status = "pending_code"
    config.phone_registered_at = None
    config.atualizado_em = datetime.utcnow()
    db.commit()

    # Solicitar código para novo número
    try:
        await solicitar_codigo(new_phone_id, "SMS")
    except MetaApiError as e:
        logger.warning(f"Erro ao solicitar código para novo número: {e.message}")

    return {
        "sucesso": True,
        "phone_number_id": new_phone_id,
        "mensagem": f"Número trocado! Código de verificação enviado para {numero_novo}.",
    }


@router.get("/painel/bot/conversas")
def listar_conversas(
    status: Optional[str] = None,
    busca: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Lista conversas do bot com paginação e busca por nome/telefone."""
    query = db.query(models.BotConversa).filter(
        models.BotConversa.restaurante_id == restaurante.id
    )
    if status:
        query = query.filter(models.BotConversa.status == status)
    if busca and busca.strip():
        termo = busca.strip()
        # Se contém dígitos (≥4), busca por telefone OU nome; senão só nome
        has_digits = sum(1 for ch in termo if ch.isdigit()) >= 4
        if has_digits:
            query = query.filter(
                sa.or_(
                    models.BotConversa.telefone.contains(termo),
                    models.BotConversa.nome_cliente.ilike(f"%{termo}%"),
                )
            )
        else:
            query = query.filter(models.BotConversa.nome_cliente.ilike(f"%{termo}%"))

    total = query.count()
    conversas = query.order_by(models.BotConversa.atualizado_em.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "conversas": [
            {
                "id": c.id,
                "telefone": c.telefone,
                "nome_cliente": c.nome_cliente,
                "status": c.status,
                "msgs_enviadas": c.msgs_enviadas,
                "msgs_recebidas": c.msgs_recebidas,
                "pedido_ativo_id": c.pedido_ativo_id,
                "intencao_atual": c.intencao_atual,
                "handoff_motivo": c.handoff_motivo,
                "handoff_em": c.handoff_em.isoformat() if c.handoff_em else None,
                "criado_em": c.criado_em.isoformat() if c.criado_em else None,
                "atualizado_em": c.atualizado_em.isoformat() if c.atualizado_em else None,
            }
            for c in conversas
        ],
    }


@router.get("/painel/bot/conversas/{conversa_id}/mensagens")
def listar_mensagens(
    conversa_id: int,
    pagina: int = 1,
    limite: int = 50,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Lista mensagens de uma conversa com paginação."""
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    query = db.query(models.BotMensagem).filter(
        models.BotMensagem.conversa_id == conversa_id,
    )
    total = query.count()
    offset = (pagina - 1) * limite
    mensagens = query.order_by(models.BotMensagem.criado_em).offset(offset).limit(limite).all()

    return {
        "conversa": {
            "id": conversa.id,
            "telefone": conversa.telefone,
            "nome_cliente": conversa.nome_cliente,
            "status": conversa.status,
        },
        "mensagens": [
            {
                "id": m.id,
                "direcao": m.direcao,
                "tipo": m.tipo,
                "conteudo": m.conteudo,
                "function_calls": m.function_calls,
                "tokens_input": m.tokens_input,
                "tokens_output": m.tokens_output,
                "tempo_resposta_ms": m.tempo_resposta_ms,
                "criado_em": m.criado_em.isoformat() if m.criado_em else None,
            }
            for m in mensagens
        ],
        "total": total,
        "paginas": (total + limite - 1) // limite,
    }


@router.post("/painel/bot/conversas/{conversa_id}/enviar-mensagem")
async def enviar_mensagem_manual(
    conversa_id: int,
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Envia mensagem manual do admin para o cliente via Evolution."""
    body = await request.json()
    texto = (body.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto é obrigatório")

    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id,
    ).first()
    if not config:
        raise HTTPException(status_code=400, detail="Bot não configurado")

    provider = getattr(config, "whatsapp_provider", "") or "evolution"
    if provider == "meta":
        if not config.meta_phone_number_id or not config.meta_access_token:
            raise HTTPException(status_code=400, detail="Meta Cloud API não configurada")
    else:
        if not config.evolution_instance:
            raise HTTPException(status_code=400, detail="Instância Evolution não configurada")

    # Enviar via cliente unificado (Meta ou Evolution)
    from ..bot import whatsapp_client as wa
    try:
        await wa.enviar_texto(conversa.telefone, texto, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar: {e}")

    # Registrar mensagem
    msg = models.BotMensagem(
        conversa_id=conversa.id,
        direcao="enviada",
        tipo="texto",
        conteudo=f"[ADMIN] {texto}",
    )
    db.add(msg)
    conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1
    conversa.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Mensagem enviada"}


@router.post("/painel/bot/conversas/{conversa_id}/escalar")
async def escalar_conversa(
    conversa_id: int,
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Admin assume controle da conversa — requer senha do admin."""
    body = await request.json()
    senha = (body.get("senha") or "").strip()
    if not senha:
        raise HTTPException(status_code=400, detail="Senha é obrigatória para assumir controle")

    if not restaurante.verificar_senha(senha):
        raise HTTPException(status_code=403, detail="Senha incorreta")

    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa.status = "handoff"
    conversa.handoff_em = datetime.utcnow()
    conversa.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Controle assumido — bot parou de responder nesta conversa"}


@router.post("/painel/bot/conversas/{conversa_id}/recusar-handoff")
async def recusar_handoff(
    conversa_id: int,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Admin recusa handoff — bot sugere que cliente ligue para o restaurante."""
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa.status = "ativa"
    conversa.atualizado_em = datetime.utcnow()
    db.commit()

    # Enviar mensagem ao cliente sugerindo ligar para o restaurante
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id,
    ).first()

    # Verificar se config tem provider configurado
    can_send = False
    if config:
        provider = getattr(config, "whatsapp_provider", "") or "evolution"
        if provider == "meta":
            can_send = bool(config.meta_phone_number_id and config.meta_access_token)
        else:
            can_send = bool(config.evolution_instance)

    if config and can_send:
        telefone_rest = restaurante.telefone or ""
        nome_atendente = config.nome_atendente or "assistente"
        mensagem = (
            f"O responsável não está disponível no momento para atendimento direto. "
            f"Para falar com um atendente humano, ligue para o restaurante"
        )
        if telefone_rest:
            mensagem += f": {telefone_rest}"
        mensagem += ". Enquanto isso, posso continuar te ajudando por aqui!"

        from ..bot import whatsapp_client as wa
        try:
            await wa.enviar_texto(conversa.telefone, mensagem, config)
            # Registrar mensagem
            msg = models.BotMensagem(
                conversa_id=conversa.id,
                direcao="enviada",
                tipo="texto",
                conteudo=mensagem,
            )
            db.add(msg)
            conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1
            db.commit()
        except Exception as e:
            logger.error(f"Erro ao enviar msg recusa handoff: {e}")

    return {"sucesso": True, "mensagem": "Handoff recusado — bot sugeriu ligar para o restaurante"}


@router.post("/painel/bot/conversas/{conversa_id}/devolver-bot")
def devolver_para_bot(
    conversa_id: int,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Devolve conversa para o bot — bot volta a responder."""
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversa.status = "ativa"
    conversa.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Conversa devolvida para o bot"}


@router.get("/painel/bot/dashboard")
def bot_dashboard(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Dashboard do bot — estatísticas."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoje - timedelta(days=7)

    # Conversas hoje
    conversas_hoje = db.query(func.count(models.BotConversa.id)).filter(
        models.BotConversa.restaurante_id == restaurante.id,
        models.BotConversa.criado_em >= hoje,
    ).scalar()

    # Conversas semana
    conversas_semana = db.query(func.count(models.BotConversa.id)).filter(
        models.BotConversa.restaurante_id == restaurante.id,
        models.BotConversa.criado_em >= semana,
    ).scalar()

    # Pedidos via bot hoje
    pedidos_bot_hoje = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == restaurante.id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= hoje,
    ).scalar()

    # Pedidos via bot semana
    pedidos_bot_semana = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == restaurante.id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= semana,
    ).scalar()

    # Faturamento via bot semana
    faturamento_bot = db.query(func.sum(models.Pedido.valor_total)).filter(
        models.Pedido.restaurante_id == restaurante.id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= semana,
        models.Pedido.status != "cancelado",
    ).scalar() or 0

    # Avaliação média
    avaliacao_media = db.query(func.avg(models.BotAvaliacao.nota)).filter(
        models.BotAvaliacao.restaurante_id == restaurante.id,
        models.BotAvaliacao.nota.isnot(None),
    ).scalar()

    # Problemas abertos
    problemas_abertos = db.query(func.count(models.BotProblema.id)).filter(
        models.BotProblema.restaurante_id == restaurante.id,
        models.BotProblema.resolvido == False,
    ).scalar()

    # Problemas semana
    problemas_semana = db.query(func.count(models.BotProblema.id)).filter(
        models.BotProblema.restaurante_id == restaurante.id,
        models.BotProblema.criado_em >= semana,
    ).scalar()

    # Total avaliações
    total_avaliacoes = db.query(func.count(models.BotAvaliacao.id)).filter(
        models.BotAvaliacao.restaurante_id == restaurante.id,
        models.BotAvaliacao.nota.isnot(None),
    ).scalar()

    # Conversas ativas agora
    conversas_ativas = db.query(func.count(models.BotConversa.id)).filter(
        models.BotConversa.restaurante_id == restaurante.id,
        models.BotConversa.status == "ativa",
    ).scalar()

    return {
        "bot_ativo": config.bot_ativo if config else False,
        "tokens_usados_hoje": config.tokens_usados_hoje if config else 0,
        "max_tokens_dia": config.max_tokens_dia if config else 50000,
        "conversas_hoje": conversas_hoje,
        "conversas_semana": conversas_semana,
        "conversas_ativas": conversas_ativas,
        "pedidos_bot_hoje": pedidos_bot_hoje,
        "pedidos_bot_semana": pedidos_bot_semana,
        "faturamento_bot": round(faturamento_bot, 2),
        "avaliacao_media": round(avaliacao_media, 1) if avaliacao_media else None,
        "total_avaliacoes": total_avaliacoes,
        "problemas_abertos": problemas_abertos,
        "problemas_semana": problemas_semana,
    }


# ==================== ENDPOINTS RELATÓRIOS ====================


def _parse_periodo(periodo: str) -> datetime:
    """Converte string de período em datetime limite."""
    dias = {"7d": 7, "30d": 30, "90d": 90}.get(periodo, 30)
    return datetime.utcnow() - timedelta(days=dias)


@router.get("/painel/bot/relatorio/eficiencia")
def relatorio_eficiencia(
    periodo: str = "30d",
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Relatório de eficiência do bot."""
    desde = _parse_periodo(periodo)
    rest_id = restaurante.id

    total_conversas = db.query(func.count(models.BotConversa.id)).filter(
        models.BotConversa.restaurante_id == rest_id,
        models.BotConversa.criado_em >= desde,
    ).scalar() or 0

    total_pedidos = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= desde,
    ).scalar() or 0

    taxa_conversao = round((total_pedidos / max(1, total_conversas)) * 100, 1)

    tempo_medio_ms = db.query(func.avg(models.BotMensagem.tempo_resposta_ms)).join(
        models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotConversa.restaurante_id == rest_id,
        models.BotMensagem.direcao == "enviada",
        models.BotMensagem.tempo_resposta_ms.isnot(None),
        models.BotMensagem.criado_em >= desde,
    ).scalar()

    escaladas = db.query(func.count(models.BotConversa.id)).filter(
        models.BotConversa.restaurante_id == rest_id,
        models.BotConversa.status == "handoff",
        models.BotConversa.criado_em >= desde,
    ).scalar() or 0

    resolvidas = total_conversas - escaladas
    taxa_resolucao = round((resolvidas / max(1, total_conversas)) * 100, 1)

    # Pedidos por dia
    pedidos_dia = db.query(
        cast(models.Pedido.data_criacao, Date).label("data"),
        func.count(models.Pedido.id).label("pedidos"),
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= desde,
    ).group_by(cast(models.Pedido.data_criacao, Date)).order_by("data").all()

    # Faturamento por dia
    fat_dia = db.query(
        cast(models.Pedido.data_criacao, Date).label("data"),
        func.sum(models.Pedido.valor_total).label("valor"),
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.origem == "whatsapp_bot",
        models.Pedido.data_criacao >= desde,
        models.Pedido.status != "cancelado",
    ).group_by(cast(models.Pedido.data_criacao, Date)).order_by("data").all()

    return {
        "total_conversas": total_conversas,
        "total_pedidos_bot": total_pedidos,
        "taxa_conversao": taxa_conversao,
        "tempo_medio_resposta_ms": int(tempo_medio_ms) if tempo_medio_ms else None,
        "conversas_escaladas": escaladas,
        "conversas_resolvidas_bot": resolvidas,
        "taxa_resolucao_bot": taxa_resolucao,
        "pedidos_por_dia": [{"data": str(r.data), "pedidos": r.pedidos} for r in pedidos_dia],
        "faturamento_por_dia": [{"data": str(r.data), "valor": round(float(r.valor or 0), 2)} for r in fat_dia],
    }


@router.get("/painel/bot/relatorio/satisfacao")
def relatorio_satisfacao(
    periodo: str = "30d",
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Relatório de satisfação do bot."""
    desde = _parse_periodo(periodo)
    rest_id = restaurante.id

    avaliacoes = db.query(models.BotAvaliacao).filter(
        models.BotAvaliacao.restaurante_id == rest_id,
        models.BotAvaliacao.nota.isnot(None),
        models.BotAvaliacao.criado_em >= desde,
    ).all()

    total = len(avaliacoes)
    notas = [a.nota for a in avaliacoes]
    media = round(sum(notas) / max(1, total), 1)

    distribuicao = {str(i): 0 for i in range(1, 6)}
    for n in notas:
        distribuicao[str(n)] = distribuicao.get(str(n), 0) + 1

    # NPS: promotores (4-5) - detratores (1-2) / total * 100
    promotores = sum(1 for n in notas if n >= 4)
    detratores = sum(1 for n in notas if n <= 2)
    nps = round(((promotores - detratores) / max(1, total)) * 100)

    # Categorias de problemas
    problemas = db.query(
        models.BotProblema.tipo,
        func.count(models.BotProblema.id).label("total"),
        func.sum(case((models.BotProblema.resolvido_automaticamente == True, 1), else_=0)).label("auto"),
    ).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.criado_em >= desde,
    ).group_by(models.BotProblema.tipo).all()

    categorias = []
    for p in problemas:
        categorias.append({
            "tipo": p.tipo,
            "total": p.total,
            "resolvido_bot": int(p.auto or 0),
        })

    # Google reviews solicitados
    reviews = db.query(func.count(models.BotAvaliacao.id)).filter(
        models.BotAvaliacao.restaurante_id == rest_id,
        models.BotAvaliacao.avaliou_maps == True,
        models.BotAvaliacao.criado_em >= desde,
    ).scalar() or 0

    satisfeitos = sum(1 for n in notas if n >= 4)
    insatisfeitos = sum(1 for n in notas if n <= 2)

    return {
        "nps": nps,
        "media_geral": media,
        "distribuicao_notas": distribuicao,
        "total_avaliacoes": total,
        "categorias_problemas": categorias,
        "google_reviews_solicitados": reviews,
        "clientes_satisfeitos": satisfeitos,
        "clientes_insatisfeitos": insatisfeitos,
    }


@router.get("/painel/bot/relatorio/clientes-inativos")
def relatorio_clientes_inativos(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Relatório de clientes inativos e repescagem."""
    rest_id = restaurante.id
    agora = datetime.utcnow()

    from sqlalchemy import text

    # Resumo por faixas de inatividade
    clientes_raw = db.execute(text("""
        SELECT
            c.id, c.nome, c.telefone,
            COUNT(p.id) as total_pedidos,
            MAX(p.data_criacao) as ultimo_pedido,
            MIN(p.data_criacao) as primeiro_pedido
        FROM clientes c
        JOIN pedidos p ON p.cliente_id = c.id
            AND p.restaurante_id = :rest_id
            AND p.status = 'entregue'
        WHERE c.restaurante_id = :rest_id
            AND c.telefone IS NOT NULL
        GROUP BY c.id, c.nome, c.telefone
        ORDER BY MAX(p.data_criacao) ASC
    """), {"rest_id": rest_id}).fetchall()

    total_clientes = len(clientes_raw)
    inativos_15_30 = 0
    inativos_30_60 = 0
    inativos_60_plus = 0
    lista_clientes = []

    for row in clientes_raw:
        cid, nome, tel, total, ultimo, primeiro = row
        if not ultimo:
            continue
        dias = (agora - ultimo).days

        if 15 <= dias < 30:
            inativos_15_30 += 1
        elif 30 <= dias < 60:
            inativos_30_60 += 1
        elif dias >= 60:
            inativos_60_plus += 1

        if dias >= 10:
            media_intervalo = None
            if total >= 2 and primeiro:
                dias_total = max(1, (ultimo - primeiro).days)
                media_intervalo = round(dias_total / max(1, total - 1), 1)

            # Última avaliação
            ult_av = db.query(models.BotAvaliacao.nota).filter(
                models.BotAvaliacao.cliente_id == cid,
                models.BotAvaliacao.restaurante_id == rest_id,
                models.BotAvaliacao.nota.isnot(None),
            ).order_by(models.BotAvaliacao.criado_em.desc()).first()

            # Repescagem enviada?
            reps = db.query(models.BotRepescagem).filter(
                models.BotRepescagem.cliente_id == cid,
                models.BotRepescagem.restaurante_id == rest_id,
            ).order_by(models.BotRepescagem.criado_em.desc()).first()

            lista_clientes.append({
                "id": cid,
                "nome": nome or "Cliente",
                "telefone": tel,
                "total_pedidos": total,
                "ultimo_pedido": ultimo.isoformat() if ultimo else None,
                "media_intervalo_dias": media_intervalo,
                "dias_inativo": dias,
                "ultima_avaliacao": ult_av[0] if ult_av else None,
                "repescagem_enviada": reps is not None,
                "retornou": reps.retornou if reps else False,
            })

    # Resumo repescagens
    total_reps = db.query(func.count(models.BotRepescagem.id)).filter(
        models.BotRepescagem.restaurante_id == rest_id,
    ).scalar() or 0
    retornaram = db.query(func.count(models.BotRepescagem.id)).filter(
        models.BotRepescagem.restaurante_id == rest_id,
        models.BotRepescagem.retornou == True,
    ).scalar() or 0

    return {
        "resumo": {
            "total_clientes": total_clientes,
            "inativos_15_30": inativos_15_30,
            "inativos_30_60": inativos_30_60,
            "inativos_60_plus": inativos_60_plus,
        },
        "repescagens": {
            "enviadas_total": total_reps,
            "retornaram": retornaram,
            "taxa_retorno": round((retornaram / max(1, total_reps)) * 100, 1),
        },
        "clientes": lista_clientes[:50],  # Limitar a 50
    }


# ==================== REPESCAGEM EM MASSA ====================

@router.post("/painel/bot/repescagem/criar-em-massa")
async def criar_repescagem_em_massa(
    request: Request,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Cria repescagem em massa para clientes inativos selecionados.
    Gera cupom exclusivo VOLTA-{primeiro_nome}-{código_único} para cada cliente."""
    import random
    import string

    body = await request.json()
    cliente_ids = body.get("cliente_ids", [])
    desconto_pct = body.get("desconto_pct", 10)
    validade_dias = body.get("validade_dias", 7)
    canal = body.get("canal", "whatsapp")  # 'whatsapp' | 'email' | 'ambos'

    if not cliente_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos um cliente")
    if len(cliente_ids) > 50:
        raise HTTPException(status_code=400, detail="Máximo 50 clientes por vez")

    rest_id = restaurante.id
    agora = datetime.utcnow()
    resultados = []

    # Buscar config do bot para Evolution API
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == rest_id,
    ).first()

    for cid in cliente_ids:
        cliente = db.query(models.Cliente).filter(
            models.Cliente.id == cid,
            models.Cliente.restaurante_id == rest_id,
        ).first()
        if not cliente:
            resultados.append({"cliente_id": cid, "status": "não encontrado"})
            continue

        # Gerar código exclusivo: VOLTA-{primeiro_nome}-{5 chars}
        primeiro_nome = (cliente.nome or "cliente").split()[0].upper()
        codigo_unico = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        cupom_codigo = f"VOLTA-{primeiro_nome}-{codigo_unico}"

        # Verificar unicidade do cupom
        while db.query(models.Promocao).filter(
            models.Promocao.restaurante_id == rest_id,
            models.Promocao.codigo_cupom == cupom_codigo,
        ).first():
            codigo_unico = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            cupom_codigo = f"VOLTA-{primeiro_nome}-{codigo_unico}"

        # Criar promoção exclusiva
        promo = models.Promocao(
            restaurante_id=rest_id,
            nome=f"Repescagem - {cliente.nome}",
            descricao=f"Cupom exclusivo de retorno para {cliente.nome}",
            tipo_desconto="percentual",
            valor_desconto=desconto_pct,
            codigo_cupom=cupom_codigo,
            data_inicio=agora,
            data_fim=agora + timedelta(days=validade_dias),
            uso_limitado=True,
            limite_usos=1,
            ativo=True,
            cliente_id=cid,
            tipo_cupom="repescagem",
        )
        db.add(promo)
        db.flush()

        # Mensagem padrão humanizada
        mensagem = (
            f"Oi, {cliente.nome.split()[0]}! Sentimos sua falta aqui no {restaurante.nome_fantasia}. "
            f"Preparamos um cupom exclusivo pra você: *{cupom_codigo}* com {desconto_pct}% de desconto! "
            f"Válido por {validade_dias} dias. Te esperamos!"
        )

        # Criar BotRepescagem
        repescagem = models.BotRepescagem(
            restaurante_id=rest_id,
            cliente_id=cid,
            cupom_codigo=cupom_codigo,
            cupom_desconto_pct=desconto_pct,
            mensagem_enviada=mensagem,
            cupom_validade_dias=validade_dias,
            canal=canal,
            promocao_id=promo.id,
        )
        db.add(repescagem)

        status_envio = "cupom_criado"

        # Enviar via WhatsApp (unificado: Meta ou Evolution)
        if canal in ("whatsapp", "ambos") and config and config.bot_ativo and cliente.telefone:
            try:
                from ..bot import whatsapp_client as wa
                await wa.enviar_texto(
                    numero=cliente.telefone,
                    texto=mensagem,
                    bot_config=config,
                )
                status_envio = "whatsapp_enviado"
            except Exception as e:
                logger.error(f"Erro WA repescagem {cid}: {e}")
                status_envio = "whatsapp_falhou"

        # Enviar via email
        if canal in ("email", "ambos") and cliente.email:
            try:
                from ..email_service import enviar_email_lembrete_cupom
                await enviar_email_lembrete_cupom(
                    email_destino=cliente.email,
                    nome=cliente.nome.split()[0],
                    codigo_cupom=cupom_codigo,
                    desconto=f"{desconto_pct}%",
                    expira=(agora + timedelta(days=validade_dias)).strftime("%d/%m/%Y"),
                    nome_restaurante=restaurante.nome_fantasia,
                )
                if status_envio == "whatsapp_enviado":
                    status_envio = "ambos_enviados"
                else:
                    status_envio = "email_enviado"
                repescagem.email_enviado = True
            except Exception as e:
                logger.error(f"Erro email repescagem {cid}: {e}")

        resultados.append({
            "cliente_id": cid,
            "nome": cliente.nome,
            "cupom": cupom_codigo,
            "status": status_envio,
        })

    db.commit()

    return {
        "sucesso": True,
        "total": len(resultados),
        "resultados": resultados,
    }


@router.get("/painel/bot/repescagem/historico")
def historico_repescagem(
    pagina: int = 1,
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Lista histórico de repescagens paginado (20/página)."""
    rest_id = restaurante.id
    por_pagina = 20
    offset = (pagina - 1) * por_pagina

    total = db.query(func.count(models.BotRepescagem.id)).filter(
        models.BotRepescagem.restaurante_id == rest_id,
    ).scalar() or 0

    repescagens = db.query(models.BotRepescagem).filter(
        models.BotRepescagem.restaurante_id == rest_id,
    ).order_by(models.BotRepescagem.criado_em.desc()).offset(offset).limit(por_pagina).all()

    items = []
    for r in repescagens:
        cliente = db.query(models.Cliente).filter(models.Cliente.id == r.cliente_id).first()
        items.append({
            "id": r.id,
            "cliente_nome": cliente.nome if cliente else "Removido",
            "cliente_telefone": cliente.telefone if cliente else None,
            "cupom_codigo": r.cupom_codigo,
            "cupom_desconto_pct": r.cupom_desconto_pct,
            "canal": r.canal or "whatsapp",
            "retornou": r.retornou,
            "lembrete_enviado": r.lembrete_enviado,
            "criado_em": r.criado_em.isoformat() if r.criado_em else None,
            "retornou_em": r.retornou_em.isoformat() if r.retornou_em else None,
        })

    return {
        "total": total,
        "pagina": pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "items": items,
    }


@router.get("/painel/bot/relatorio/erros-contornados")
def relatorio_erros_contornados(
    periodo: str = "30d",
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Relatório de erros contornados pelo bot."""
    desde = _parse_periodo(periodo)
    rest_id = restaurante.id

    total = db.query(func.count(models.BotProblema.id)).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.criado_em >= desde,
    ).scalar() or 0

    auto_resolvidos = db.query(func.count(models.BotProblema.id)).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.resolvido_automaticamente == True,
        models.BotProblema.criado_em >= desde,
    ).scalar() or 0

    escalados = total - auto_resolvidos
    taxa = round((auto_resolvidos / max(1, total)) * 100, 1)

    # Cupons gerados
    cupons = db.query(func.count(models.BotProblema.id)).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.cupom_gerado.isnot(None),
        models.BotProblema.criado_em >= desde,
    ).scalar() or 0

    # Valor total descontos (estimativa)
    descontos = db.query(func.sum(models.BotProblema.desconto_pct)).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.desconto_pct.isnot(None),
        models.BotProblema.criado_em >= desde,
    ).scalar() or 0

    # Por tipo
    por_tipo = db.query(
        models.BotProblema.tipo,
        func.count(models.BotProblema.id).label("total"),
        func.sum(case((models.BotProblema.resolvido_automaticamente == True, 1), else_=0)).label("auto_resolvidos"),
        func.sum(case((models.BotProblema.resolvido_automaticamente != True, 1), else_=0)).label("escalados"),
    ).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.criado_em >= desde,
    ).group_by(models.BotProblema.tipo).all()

    # Por política
    por_politica = db.query(
        models.BotProblema.resolucao_tipo,
        func.count(models.BotProblema.id).label("vezes"),
    ).filter(
        models.BotProblema.restaurante_id == rest_id,
        models.BotProblema.resolucao_tipo.isnot(None),
        models.BotProblema.criado_em >= desde,
    ).group_by(models.BotProblema.resolucao_tipo).all()

    return {
        "total_problemas": total,
        "resolvidos_bot": auto_resolvidos,
        "escalados_humano": escalados,
        "taxa_resolucao_automatica": taxa,
        "cupons_gerados": cupons,
        "valor_descontos_estimado": round(float(descontos), 2),
        "por_tipo": [
            {"tipo": r.tipo, "total": r.total, "auto_resolvidos": int(r.auto_resolvidos or 0), "escalados": int(r.escalados or 0)}
            for r in por_tipo
        ],
        "por_politica": [
            {"acao": r.resolucao_tipo, "vezes_usada": r.vezes}
            for r in por_politica
        ],
    }


# ==================== ENDPOINTS SUPER ADMIN ====================

@router.get("/api/admin/bot/instancias")
def listar_instancias_bot(
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Lista todos os bots configurados (Super Admin)."""
    configs = db.query(models.BotConfig).all()

    result = []
    for c in configs:
        rest = db.query(models.Restaurante).filter(models.Restaurante.id == c.restaurante_id).first()
        result.append({
            "id": c.id,
            "restaurante_id": c.restaurante_id,
            "restaurante_nome": rest.nome_fantasia if rest else "?",
            "bot_ativo": c.bot_ativo,
            "whatsapp_provider": getattr(c, "whatsapp_provider", "evolution") or "evolution",
            "whatsapp_numero": c.whatsapp_numero,
            "evolution_instance": c.evolution_instance,
            "meta_phone_number_id": getattr(c, "meta_phone_number_id", None),
            "nome_atendente": c.nome_atendente,
            "tokens_usados_hoje": c.tokens_usados_hoje,
            "criado_em": c.criado_em.isoformat() if c.criado_em else None,
        })

    return result


@router.post("/api/admin/bot/criar-instancia/{restaurante_id}")
async def criar_instancia_bot(
    restaurante_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Cria instância do bot WhatsApp para um restaurante (Super Admin)."""
    body = await request.json()

    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Verificar se já existe
    existente = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante_id
    ).first()

    if existente:
        # Atualizar config (Evolution ou Meta)
        existente.whatsapp_provider = body.get("whatsapp_provider", existente.whatsapp_provider or "evolution")
        existente.evolution_instance = body.get("evolution_instance", existente.evolution_instance)
        existente.evolution_api_url = body.get("evolution_api_url", existente.evolution_api_url)
        existente.evolution_api_key = body.get("evolution_api_key", existente.evolution_api_key)
        existente.whatsapp_numero = body.get("whatsapp_numero", existente.whatsapp_numero)
        # Meta Cloud API fields
        for meta_field in ("meta_phone_number_id", "meta_access_token", "meta_waba_id", "meta_app_secret", "meta_webhook_verify_token"):
            if meta_field in body:
                setattr(existente, meta_field, body[meta_field])
        existente.atualizado_em = datetime.utcnow()
        db.commit()
        return {"sucesso": True, "id": existente.id, "mensagem": "Instância atualizada"}

    # Criar nova
    config = models.BotConfig(
        restaurante_id=restaurante_id,
        bot_ativo=body.get("bot_ativo", False),
        whatsapp_provider=body.get("whatsapp_provider", "evolution"),
        nome_atendente=body.get("nome_atendente", "Bia"),
        tom_personalidade=body.get("tom_personalidade", "informal amigável"),
        voz_tts=body.get("voz_tts", "ara"),
        evolution_instance=body.get("evolution_instance"),
        evolution_api_url=body.get("evolution_api_url"),
        evolution_api_key=body.get("evolution_api_key"),
        whatsapp_numero=body.get("whatsapp_numero"),
        # Meta Cloud API
        meta_phone_number_id=body.get("meta_phone_number_id"),
        meta_access_token=body.get("meta_access_token"),
        meta_waba_id=body.get("meta_waba_id"),
        meta_app_secret=body.get("meta_app_secret"),
        meta_webhook_verify_token=body.get("meta_webhook_verify_token"),
    )
    db.add(config)
    db.commit()

    return {"sucesso": True, "id": config.id, "mensagem": f"Bot WhatsApp criado para {rest.nome_fantasia}"}


@router.put("/api/admin/bot/instancia/{config_id}")
async def atualizar_instancia_bot(
    config_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza instância do bot (Super Admin pode alterar tudo)."""
    body = await request.json()

    config = db.query(models.BotConfig).filter(models.BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Instância não encontrada")

    for campo in ADMIN_BOT_CAMPOS_PERMITIDOS:
        if campo in body and hasattr(config, campo):
            setattr(config, campo, body[campo])

    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Instância atualizada"}


@router.get("/api/admin/bot/token-usage")
def token_usage_dashboard(
    periodo: str = "daily",
    restaurante_id: Optional[int] = None,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Dashboard de uso de tokens do bot — Super Admin.
    periodo: daily (hoje), weekly (7 dias), monthly (30 dias)
    """
    dias = {"daily": 1, "weekly": 7, "monthly": 30}.get(periodo, 1)
    desde = datetime.utcnow() - timedelta(days=dias)

    # Base query: mensagens enviadas pelo bot (com tokens)
    base_q = (
        db.query(models.BotMensagem)
        .join(models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id)
        .filter(
            models.BotMensagem.direcao == "enviada",
            models.BotMensagem.criado_em >= desde,
        )
    )
    if restaurante_id:
        base_q = base_q.filter(models.BotConversa.restaurante_id == restaurante_id)

    # Totais agregados
    totais = db.query(
        func.coalesce(func.sum(models.BotMensagem.tokens_input), 0).label("tokens_input"),
        func.coalesce(func.sum(models.BotMensagem.tokens_output), 0).label("tokens_output"),
        func.count(models.BotMensagem.id).label("total_mensagens"),
    ).select_from(models.BotMensagem).join(
        models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotMensagem.direcao == "enviada",
        models.BotMensagem.criado_em >= desde,
    )
    if restaurante_id:
        totais = totais.filter(models.BotConversa.restaurante_id == restaurante_id)
    totais = totais.first()

    tokens_in = int(totais.tokens_input or 0)
    tokens_out = int(totais.tokens_output or 0)

    # Pricing xAI Grok-3-mini-fast: $0.30/1M input, $0.50/1M output
    custo_usd = (tokens_in * 0.30 / 1_000_000) + (tokens_out * 0.50 / 1_000_000)
    custo_brl = custo_usd * 5.7  # taxa aproximada

    # Restaurantes ativos no período
    rest_ativos_q = db.query(
        func.count(sa.distinct(models.BotConversa.restaurante_id))
    ).join(
        models.BotMensagem, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotMensagem.direcao == "enviada",
        models.BotMensagem.criado_em >= desde,
    )
    if restaurante_id:
        rest_ativos_q = rest_ativos_q.filter(models.BotConversa.restaurante_id == restaurante_id)
    restaurantes_ativos = rest_ativos_q.scalar() or 0

    # Áudio STT (mensagens recebidas tipo=audio)
    audio_q = db.query(
        func.count(models.BotMensagem.id).label("total"),
    ).select_from(models.BotMensagem).join(
        models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotMensagem.tipo == "audio",
        models.BotMensagem.direcao == "recebida",
        models.BotMensagem.criado_em >= desde,
    )
    if restaurante_id:
        audio_q = audio_q.filter(models.BotConversa.restaurante_id == restaurante_id)
    audio_total = audio_q.scalar() or 0

    # Por restaurante
    por_rest_q = db.query(
        models.BotConversa.restaurante_id,
        func.coalesce(func.sum(models.BotMensagem.tokens_input), 0).label("tokens_in"),
        func.coalesce(func.sum(models.BotMensagem.tokens_output), 0).label("tokens_out"),
        func.count(models.BotMensagem.id).label("mensagens"),
    ).join(
        models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotMensagem.direcao == "enviada",
        models.BotMensagem.criado_em >= desde,
    )
    if restaurante_id:
        por_rest_q = por_rest_q.filter(models.BotConversa.restaurante_id == restaurante_id)
    por_rest_q = por_rest_q.group_by(models.BotConversa.restaurante_id).all()

    por_restaurante = []
    for row in por_rest_q:
        rest = db.query(models.Restaurante).filter(models.Restaurante.id == row.restaurante_id).first()
        ti = int(row.tokens_in or 0)
        to_ = int(row.tokens_out or 0)
        custo_r = (ti * 0.30 / 1_000_000) + (to_ * 0.50 / 1_000_000)
        por_restaurante.append({
            "restaurante_id": row.restaurante_id,
            "nome": rest.nome_fantasia if rest else "?",
            "plano": rest.plano if rest else "?",
            "tokens_input": ti,
            "tokens_output": to_,
            "mensagens": row.mensagens,
            "custo_usd": round(custo_r, 4),
            "custo_brl": round(custo_r * 5.7, 2),
        })
    por_restaurante.sort(key=lambda x: x["custo_usd"], reverse=True)

    # Chart diário
    chart_q = db.query(
        cast(models.BotMensagem.criado_em, Date).label("dia"),
        func.coalesce(func.sum(models.BotMensagem.tokens_input), 0).label("tokens_input"),
        func.coalesce(func.sum(models.BotMensagem.tokens_output), 0).label("tokens_output"),
        func.count(models.BotMensagem.id).label("mensagens"),
    ).join(
        models.BotConversa, models.BotMensagem.conversa_id == models.BotConversa.id
    ).filter(
        models.BotMensagem.direcao == "enviada",
        models.BotMensagem.criado_em >= desde,
    )
    if restaurante_id:
        chart_q = chart_q.filter(models.BotConversa.restaurante_id == restaurante_id)
    chart_q = chart_q.group_by(cast(models.BotMensagem.criado_em, Date)).order_by("dia").all()

    chart_diario = []
    for row in chart_q:
        ti = int(row.tokens_input or 0)
        to_ = int(row.tokens_output or 0)
        chart_diario.append({
            "dia": str(row.dia),
            "tokens_input": ti,
            "tokens_output": to_,
            "mensagens": row.mensagens,
            "custo_usd": round((ti * 0.30 / 1_000_000) + (to_ * 0.50 / 1_000_000), 4),
        })

    return {
        "totais": {
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "total_mensagens": totais.total_mensagens,
            "custo_usd": round(custo_usd, 4),
            "custo_brl": round(custo_brl, 2),
            "restaurantes_ativos": restaurantes_ativos,
        },
        "audio_stt": {
            "total_transcricoes": audio_total,
        },
        "por_restaurante": por_restaurante,
        "chart_diario": chart_diario,
    }


@router.delete("/api/admin/bot/instancia/{config_id}")
def deletar_instancia_bot(
    config_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Deleta instância do bot (Super Admin)."""
    config = db.query(models.BotConfig).filter(models.BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Instância não encontrada")

    db.delete(config)
    db.commit()

    return {"sucesso": True, "mensagem": "Instância deletada"}


# ==================== POOL DE NÚMEROS — SUPER ADMIN ====================

@router.get("/api/admin/bot/{rest_id}/pool")
def listar_pool(
    rest_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Lista pool de números WhatsApp de um restaurante (Super Admin)."""
    from ..bot.phone_pool import get_pool_status
    return get_pool_status(db, rest_id)


@router.post("/api/admin/bot/{rest_id}/pool")
async def adicionar_numero_pool(
    rest_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Adiciona número ao pool de um restaurante (Super Admin)."""
    data = await request.json()

    # Validações
    if not data.get("evolution_instance"):
        raise HTTPException(400, "evolution_instance é obrigatório")
    if not data.get("whatsapp_numero"):
        raise HTTPException(400, "whatsapp_numero é obrigatório")
    if not data.get("evolution_api_url"):
        raise HTTPException(400, "evolution_api_url é obrigatório")
    if not data.get("evolution_api_key"):
        raise HTTPException(400, "evolution_api_key é obrigatório")

    # Verificar se instance já existe
    existe = db.query(models.BotPhonePool).filter(
        models.BotPhonePool.evolution_instance == data["evolution_instance"],
    ).first()
    if existe:
        raise HTTPException(400, f"Instância '{data['evolution_instance']}' já existe no pool")

    # Calcular próxima posição na fila
    max_pos = db.query(func.max(models.BotPhonePool.posicao_fila)).filter(
        models.BotPhonePool.restaurante_id == rest_id,
    ).scalar() or -1

    status = data.get("status", "em_aquecimento")
    if status not in ("standby", "em_aquecimento", "ativo"):
        status = "em_aquecimento"

    entry = models.BotPhonePool(
        restaurante_id=rest_id,
        evolution_instance=data["evolution_instance"],
        evolution_api_url=data["evolution_api_url"],
        evolution_api_key=data["evolution_api_key"],
        whatsapp_numero=data["whatsapp_numero"],
        status=status,
        posicao_fila=max_pos + 1,
        aquecimento_inicio=datetime.utcnow() if status == "em_aquecimento" else None,
        ativado_em=datetime.utcnow() if status == "ativo" else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "sucesso": True,
        "id": entry.id,
        "status": entry.status,
        "posicao_fila": entry.posicao_fila,
    }


@router.put("/api/admin/bot/pool/{pool_id}")
async def atualizar_pool_entry(
    pool_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza entry do pool (Super Admin)."""
    entry = db.query(models.BotPhonePool).filter(models.BotPhonePool.id == pool_id).first()
    if not entry:
        raise HTTPException(404, "Entry não encontrada")

    data = await request.json()
    campos_permitidos = {
        "evolution_instance", "evolution_api_url", "evolution_api_key",
        "whatsapp_numero", "status", "posicao_fila",
    }
    for campo, valor in data.items():
        if campo in campos_permitidos:
            if campo == "status" and valor == "ativo":
                entry.ativado_em = datetime.utcnow()
            elif campo == "status" and valor == "em_aquecimento":
                entry.aquecimento_inicio = datetime.utcnow()
                entry.aquecimento_msgs_hoje = 0
            setattr(entry, campo, valor)

    entry.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "id": entry.id, "status": entry.status}


@router.delete("/api/admin/bot/pool/{pool_id}")
def deletar_pool_entry(
    pool_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Remove número do pool (Super Admin)."""
    entry = db.query(models.BotPhonePool).filter(models.BotPhonePool.id == pool_id).first()
    if not entry:
        raise HTTPException(404, "Entry não encontrada")
    if entry.status == "ativo":
        raise HTTPException(400, "Não é possível remover o número ativo. Rotacione primeiro.")

    db.delete(entry)
    db.commit()
    return {"sucesso": True}


@router.post("/api/admin/bot/{rest_id}/pool/rotacionar")
async def rotacionar_numero_manual(
    rest_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Rotação manual de número (Super Admin)."""
    data = await request.json()
    motivo = data.get("motivo", "rotacao_manual")

    from ..bot.phone_pool import rotate_number, recover_conversations
    new_entry = rotate_number(db, rest_id, motivo, data.get("detalhes", ""))

    if not new_entry:
        raise HTTPException(400, "Sem números standby disponíveis no pool")

    # Recuperar conversas afetadas
    bot_config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == rest_id,
    ).first()
    notificados = 0
    if bot_config and data.get("notificar_clientes", True):
        old_number = data.get("numero_anterior") or ""
        notificados = await recover_conversations(db, rest_id, old_number, new_entry, bot_config)

    return {
        "sucesso": True,
        "numero_novo": new_entry.whatsapp_numero,
        "instance_nova": new_entry.evolution_instance,
        "clientes_notificados": notificados,
    }


@router.get("/api/admin/bot/{rest_id}/pool/log")
def listar_log_rotacoes(
    rest_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
    limit: int = 50,
):
    """Histórico de rotações de número (Super Admin)."""
    logs = db.query(models.BotRotacaoLog).filter(
        models.BotRotacaoLog.restaurante_id == rest_id,
    ).order_by(models.BotRotacaoLog.criado_em.desc()).limit(limit).all()

    return [{
        "id": log.id,
        "numero_anterior": log.numero_anterior,
        "numero_novo": log.numero_novo,
        "instance_anterior": log.instance_anterior,
        "instance_nova": log.instance_nova,
        "motivo": log.motivo,
        "detalhes": log.detalhes,
        "conversas_afetadas": log.conversas_afetadas,
        "criado_em": log.criado_em.isoformat() if log.criado_em else None,
    } for log in logs]


# ==================== POOL DE NÚMEROS — RESTAURANTE (read-only) ====================

@router.get("/painel/bot/pool/status")
def get_pool_status_restaurante(
    restaurante: models.Restaurante = Depends(get_current_restaurante),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Status do pool de números para o restaurante (read-only)."""
    from ..bot.phone_pool import get_pool_status
    status = get_pool_status(db, restaurante.id)

    # Sanitizar: restaurante não deve ver api_keys
    for numero in status.get("numeros", []):
        numero.pop("evolution_api_key", None)
        numero.pop("evolution_api_url", None)
        numero.pop("evolution_instance", None)

    return status


# ==================== META GATEWAY — SUPER ADMIN ====================

@router.get("/api/admin/bot/{rest_id}/meta-gateway")
def get_meta_gateway(
    rest_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Retorna configuração do gateway Meta de um restaurante (Super Admin)."""
    gw = db.query(models.BotMetaGateway).filter(
        models.BotMetaGateway.restaurante_id == rest_id,
    ).first()
    if not gw:
        return {"configurado": False}

    return {
        "configurado": True,
        "id": gw.id,
        "phone_number_id": gw.phone_number_id,
        "waba_id": gw.waba_id,
        "whatsapp_numero": gw.whatsapp_numero,
        "template_redirect_nome": gw.template_redirect_nome,
        "template_recovery_nome": gw.template_recovery_nome,
        "ativo": gw.ativo,
        "criado_em": gw.criado_em.isoformat() if gw.criado_em else None,
    }


@router.post("/api/admin/bot/{rest_id}/meta-gateway")
async def criar_meta_gateway(
    rest_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Configura gateway Meta para um restaurante (Super Admin)."""
    data = await request.json()

    required = ["phone_number_id", "access_token", "whatsapp_numero", "webhook_verify_token"]
    for field in required:
        if not data.get(field):
            raise HTTPException(400, f"{field} é obrigatório")

    # Verificar se já existe
    existing = db.query(models.BotMetaGateway).filter(
        models.BotMetaGateway.restaurante_id == rest_id,
    ).first()
    if existing:
        raise HTTPException(400, "Gateway Meta já configurado para este restaurante. Use PUT para atualizar.")

    gw = models.BotMetaGateway(
        restaurante_id=rest_id,
        phone_number_id=data["phone_number_id"],
        access_token=data["access_token"],
        waba_id=data.get("waba_id"),
        whatsapp_numero=data["whatsapp_numero"],
        webhook_verify_token=data["webhook_verify_token"],
        template_redirect_nome=data.get("template_redirect_nome", "redirect_atendimento"),
        template_recovery_nome=data.get("template_recovery_nome", "numero_atualizado"),
    )
    db.add(gw)
    db.commit()
    db.refresh(gw)

    return {"sucesso": True, "id": gw.id}


@router.put("/api/admin/bot/{rest_id}/meta-gateway")
async def atualizar_meta_gateway(
    rest_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza gateway Meta (Super Admin)."""
    gw = db.query(models.BotMetaGateway).filter(
        models.BotMetaGateway.restaurante_id == rest_id,
    ).first()
    if not gw:
        raise HTTPException(404, "Gateway Meta não encontrado")

    data = await request.json()
    campos_permitidos = {
        "phone_number_id", "access_token", "waba_id", "whatsapp_numero",
        "webhook_verify_token", "template_redirect_nome", "template_recovery_nome", "ativo",
    }
    for campo, valor in data.items():
        if campo in campos_permitidos:
            setattr(gw, campo, valor)

    gw.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True}


@router.delete("/api/admin/bot/{rest_id}/meta-gateway")
def deletar_meta_gateway(
    rest_id: int,
    admin: models.SuperAdmin = Depends(get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Remove gateway Meta (Super Admin)."""
    gw = db.query(models.BotMetaGateway).filter(
        models.BotMetaGateway.restaurante_id == rest_id,
    ).first()
    if not gw:
        raise HTTPException(404, "Gateway Meta não encontrado")

    db.delete(gw)
    db.commit()
    return {"sucesso": True}
