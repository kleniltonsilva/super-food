"""
Router Bot WhatsApp Humanoide — Webhook Evolution + Endpoints Admin + Super Admin.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
import logging

from .. import models, database
from ..auth import get_restaurante_logado, get_admin_logado
from ..feature_guard import verificar_feature

logger = logging.getLogger("superfood.bot.router")

router = APIRouter(tags=["Bot WhatsApp"])


# ==================== WEBHOOK EVOLUTION API (público) ====================

@router.post("/webhooks/evolution")
async def webhook_evolution(request: Request):
    """Webhook público da Evolution API. Responde 200 imediatamente e processa em background."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "ok"})

    from ..bot.atendente import processar_webhook
    resultado = await processar_webhook(payload)

    return JSONResponse({"status": "ok", **resultado})


# ==================== ENDPOINTS PAINEL RESTAURANTE ====================

@router.get("/painel/bot/config")
def get_bot_config(
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
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
        "nome_atendente": config.nome_atendente,
        "tom_personalidade": config.tom_personalidade,
        "voz_tts": config.voz_tts,
        "idioma": config.idioma,
        "whatsapp_numero": config.whatsapp_numero,
        "evolution_instance": config.evolution_instance,
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
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
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
        "impressao_automatica_bot",
        "stt_ativo", "tts_autonomo",
    ]

    for campo in campos_permitidos:
        if campo in body:
            setattr(config, campo, body[campo])

    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Configuração do bot atualizada"}


@router.post("/painel/bot/ativar")
def ativar_bot(
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Ativa o bot WhatsApp (requer config prévia pelo Super Admin)."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="Bot não configurado. Solicite ativação pelo Super Admin.")

    if not config.evolution_instance or not config.evolution_api_url:
        raise HTTPException(status_code=400, detail="Instância Evolution não configurada. Contate o suporte.")

    config.bot_ativo = True
    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Bot WhatsApp ativado!"}


@router.post("/painel/bot/desativar")
def desativar_bot(
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
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


@router.get("/painel/bot/conversas")
def listar_conversas(
    status: Optional[str] = None,
    limit: int = 50,
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Lista conversas do bot."""
    query = db.query(models.BotConversa).filter(
        models.BotConversa.restaurante_id == restaurante.id
    )
    if status:
        query = query.filter(models.BotConversa.status == status)

    conversas = query.order_by(models.BotConversa.atualizado_em.desc()).limit(limit).all()

    return [
        {
            "id": c.id,
            "telefone": c.telefone,
            "nome_cliente": c.nome_cliente,
            "status": c.status,
            "msgs_enviadas": c.msgs_enviadas,
            "msgs_recebidas": c.msgs_recebidas,
            "pedido_ativo_id": c.pedido_ativo_id,
            "intencao_atual": c.intencao_atual,
            "criado_em": c.criado_em.isoformat() if c.criado_em else None,
            "atualizado_em": c.atualizado_em.isoformat() if c.atualizado_em else None,
        }
        for c in conversas
    ]


@router.get("/painel/bot/conversas/{conversa_id}/mensagens")
def listar_mensagens(
    conversa_id: int,
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
    _feature: None = Depends(verificar_feature("bot_whatsapp")),
    db: Session = Depends(database.get_db),
):
    """Lista mensagens de uma conversa."""
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.id == conversa_id,
        models.BotConversa.restaurante_id == restaurante.id,
    ).first()

    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    mensagens = db.query(models.BotMensagem).filter(
        models.BotMensagem.conversa_id == conversa_id,
    ).order_by(models.BotMensagem.criado_em).all()

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
    }


@router.get("/painel/bot/dashboard")
def bot_dashboard(
    restaurante: models.Restaurante = Depends(get_restaurante_logado),
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


# ==================== ENDPOINTS SUPER ADMIN ====================

@router.get("/api/admin/bot/instancias")
def listar_instancias_bot(
    admin: models.SuperAdmin = Depends(get_admin_logado),
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
            "whatsapp_numero": c.whatsapp_numero,
            "evolution_instance": c.evolution_instance,
            "nome_atendente": c.nome_atendente,
            "tokens_usados_hoje": c.tokens_usados_hoje,
            "criado_em": c.criado_em.isoformat() if c.criado_em else None,
        })

    return result


@router.post("/api/admin/bot/criar-instancia/{restaurante_id}")
async def criar_instancia_bot(
    restaurante_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_admin_logado),
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
        # Atualizar Evolution config
        existente.evolution_instance = body.get("evolution_instance", existente.evolution_instance)
        existente.evolution_api_url = body.get("evolution_api_url", existente.evolution_api_url)
        existente.evolution_api_key = body.get("evolution_api_key", existente.evolution_api_key)
        existente.whatsapp_numero = body.get("whatsapp_numero", existente.whatsapp_numero)
        existente.atualizado_em = datetime.utcnow()
        db.commit()
        return {"sucesso": True, "id": existente.id, "mensagem": "Instância atualizada"}

    # Criar nova
    config = models.BotConfig(
        restaurante_id=restaurante_id,
        bot_ativo=body.get("bot_ativo", False),
        nome_atendente=body.get("nome_atendente", "Bia"),
        tom_personalidade=body.get("tom_personalidade", "informal amigável"),
        voz_tts=body.get("voz_tts", "ara"),
        evolution_instance=body.get("evolution_instance"),
        evolution_api_url=body.get("evolution_api_url"),
        evolution_api_key=body.get("evolution_api_key"),
        whatsapp_numero=body.get("whatsapp_numero"),
    )
    db.add(config)
    db.commit()

    return {"sucesso": True, "id": config.id, "mensagem": f"Bot WhatsApp criado para {rest.nome_fantasia}"}


@router.put("/api/admin/bot/instancia/{config_id}")
async def atualizar_instancia_bot(
    config_id: int,
    request: Request,
    admin: models.SuperAdmin = Depends(get_admin_logado),
    db: Session = Depends(database.get_db),
):
    """Atualiza instância do bot (Super Admin pode alterar tudo)."""
    body = await request.json()

    config = db.query(models.BotConfig).filter(models.BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Instância não encontrada")

    for campo, valor in body.items():
        if hasattr(config, campo):
            setattr(config, campo, valor)

    config.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "mensagem": "Instância atualizada"}


@router.delete("/api/admin/bot/instancia/{config_id}")
def deletar_instancia_bot(
    config_id: int,
    admin: models.SuperAdmin = Depends(get_admin_logado),
    db: Session = Depends(database.get_db),
):
    """Deleta instância do bot (Super Admin)."""
    config = db.query(models.BotConfig).filter(models.BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Instância não encontrada")

    db.delete(config)
    db.commit()

    return {"sucesso": True, "mensagem": "Instância deletada"}
