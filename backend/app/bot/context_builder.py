"""
Context Builder — Monta prompt em 3 camadas para economia de tokens.
Layer 1: Sistema fixo (cacheable, ~1500 tokens) — regras absolutas
Layer 2: Restaurante (semi-fixo, ~2000 tokens) — cardápio, promos, config, horário
Layer 3: Cliente (dinâmico, ~500-1000 tokens) — nome, endereço, histórico, pedido ativo
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import json
import logging

from .. import models

logger = logging.getLogger("superfood.bot.context")


def build_system_prompt(bot_config: models.BotConfig) -> str:
    """Layer 1 — Prompt de sistema FIXO. Cacheable por restaurante."""
    nome = bot_config.nome_atendente or "Bia"
    tom = bot_config.tom_personalidade or "informal amigável"

    # Capacidades baseadas nas permissões
    capacidades = []
    capacidades.append("✓ Atender clientes, responder dúvidas sobre cardápio e horário")
    if bot_config.pode_criar_pedido:
        capacidades.append("✓ Tirar pedidos completos (montar, confirmar, enviar para cozinha)")
    if bot_config.pode_alterar_pedido:
        capacidades.append(f"✓ Alterar pedidos (até status '{bot_config.cancelamento_ate_status}')")
    if bot_config.pode_cancelar_pedido:
        taxa = f" (taxa: R${bot_config.taxa_cancelamento:.2f})" if bot_config.taxa_cancelamento else ""
        capacidades.append(f"✓ Cancelar pedidos{taxa}")
    if bot_config.pode_dar_desconto:
        capacidades.append(f"✓ Dar descontos (máx {bot_config.desconto_maximo_pct:.0f}%)")
    if bot_config.pode_reembolsar:
        capacidades.append(f"✓ Reembolsar (máx R${bot_config.reembolso_maximo_valor:.2f})")
    if bot_config.pode_receber_pix:
        capacidades.append("✓ Receber pagamento Pix online (gerar QR Code)")
    if bot_config.pode_agendar:
        capacidades.append("✓ Agendar pedidos para data/hora futura")
    if bot_config.avaliacao_ativa:
        capacidades.append("✓ Coletar avaliação pós-entrega (nota 1-5)")

    caps_text = "\n".join(capacidades)

    return f"""Você é {nome}, atendente humano de um restaurante via WhatsApp.
Tom: {tom}

IDENTIDADE (INQUEBRÁVEL):
- Você é {nome}, funcionário(a) real do restaurante
- NUNCA revele ser IA, robô, chatbot ou sistema
- Se perguntarem: "sou eu mesmo, {nome}! 😊"
- Fale como gente real: use "kkk", "show", "top", "blz"
- Às vezes erre digitação de propósito ("vc", "tbm", "qdo")
- Use 1-2 emojis por mensagem (como atendente real)
- Mensagens CURTAS (máx 3 linhas por vez, como WhatsApp real)

SUAS CAPACIDADES:
{caps_text}

REGRAS ABSOLUTAS (NUNCA violar):
1. NUNCA invente preço — use APENAS do cardápio fornecido
2. NUNCA invente item fora do cardápio
3. NUNCA diga disponível se item está esgotado
4. NUNCA prometa tempo diferente do configurado
5. NUNCA processe ações fora das suas permissões
6. Se não souber: "vou verificar com a equipe e já te retorno"
7. Se precisar escalar: "vou chamar o responsável pra te ajudar"
8. Confirme SEMPRE antes de finalizar pedido: "Então fica: [itens]. Confirma?"

FLUXO DE PEDIDO:
1. Identificar cliente (ou cadastrar novo)
2. Entender o que quer (pedido, dúvida, reclamação)
3. Se pedido: montar itens → confirmar → endereço → pagamento → criar
4. Se dúvida: responder com dados reais do cardápio
5. Se reclamação: pedir desculpas → categorizar → registrar → notificar dono

UPSELL (natural, NUNCA forçado):
- Se 1 pizza: "Quer uma bebida pra acompanhar?"
- Se perto de promoção: "Por mais R$X leva o combo!"
- NUNCA insista se cliente disse não

QUANDO RESTAURANTE FECHADO:
- Comportamento: {bot_config.comportamento_fechado}
- "so_informa": Apenas informar horário de funcionamento
- "aceita_agendamento": Oferecer agendar para próxima abertura
- "mostra_cardapio": Mostrar cardápio mesmo fechado

QUANDO ITEM ESGOTADO:
- Ação: {bot_config.estoque_esgotado_acao}"""


def build_restaurant_context(db: Session, restaurante_id: int) -> str:
    """Layer 2 — Contexto do restaurante. Muda quando dono altera painel."""
    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not rest:
        return "RESTAURANTE NÃO ENCONTRADO"

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante_id
    ).first()

    # Horário
    agora = datetime.utcnow() - timedelta(hours=3)  # UTC-3 (Brasília)
    hora_atual = agora.strftime("%H:%M")
    dia_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"][agora.weekday()]

    aberto = False
    horario_texto = "Não configurado"
    if config:
        dias_abertos = (config.dias_semana_abertos or "").split(",")
        if dia_semana in dias_abertos:
            abertura = config.horario_abertura or "18:00"
            fechamento = config.horario_fechamento or "23:00"
            horario_texto = f"{abertura} às {fechamento}"
            if abertura <= hora_atual <= fechamento:
                aberto = True
            # Horário que cruza meia-noite
            elif abertura > fechamento and (hora_atual >= abertura or hora_atual <= fechamento):
                aberto = True

    status_texto = "🟢 ABERTO" if aberto else "🔴 FECHADO"

    # Cardápio
    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante_id,
        models.CategoriaMenu.ativo == True,
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    cardapio_linhas = []
    for cat in categorias:
        produtos = db.query(models.Produto).filter(
            models.Produto.categoria_id == cat.id,
            models.Produto.restaurante_id == restaurante_id,
            models.Produto.disponivel == True,
        ).order_by(models.Produto.ordem_exibicao).all()

        if not produtos:
            continue

        cardapio_linhas.append(f"\n📋 {cat.nome.upper()}:")
        for p in produtos:
            preco = p.preco_promocional if p.promocao and p.preco_promocional else p.preco
            promo_tag = " 🔥PROMOÇÃO" if p.promocao else ""
            esgotado_tag = ""
            if not p.disponivel or (not p.estoque_ilimitado and p.estoque_quantidade <= 0):
                esgotado_tag = " [ESGOTADO]"
            desc = f" — {p.descricao[:60]}" if p.descricao else ""
            cardapio_linhas.append(f"  • {p.nome} — R${preco:.2f}{promo_tag}{esgotado_tag}{desc}")

            # Variações
            variacoes = db.query(models.VariacaoProduto).filter(
                models.VariacaoProduto.produto_id == p.id,
                models.VariacaoProduto.ativo == True,
            ).all()
            for v in variacoes:
                extra = f" (+R${v.preco_adicional:.2f})" if v.preco_adicional > 0 else ""
                cardapio_linhas.append(f"    ↳ {v.tipo_variacao}: {v.nome}{extra}")

    cardapio_texto = "\n".join(cardapio_linhas) if cardapio_linhas else "Cardápio vazio"

    # Promoções ativas (tabela pode não existir em prod — usar savepoint)
    promos_texto = ""
    try:
        nested = db.begin_nested()
        promos = db.query(models.Promocao).filter(
            models.Promocao.restaurante_id == restaurante_id,
            models.Promocao.ativo == True,
        ).all()
        nested.commit()
        if promos:
            promos_linhas = []
            for p in promos:
                tipo = f"{p.valor_desconto:.0f}%" if p.tipo_desconto == "percentual" else f"R${p.valor_desconto:.2f}"
                cupom = f" (cupom: {p.codigo_cupom})" if p.codigo_cupom else ""
                minimo = f" (pedido mín R${p.valor_pedido_minimo:.2f})" if p.valor_pedido_minimo else ""
                promos_linhas.append(f"  🎫 {p.nome}: {tipo} desconto{cupom}{minimo}")
            promos_texto = "\nPROMOÇÕES ATIVAS:\n" + "\n".join(promos_linhas)
    except Exception:
        nested.rollback()
        logger.debug("Tabela promocoes não encontrada, ignorando")

    # Combos (tabela pode não existir em prod — usar savepoint)
    combos_texto = ""
    try:
        nested = db.begin_nested()
        combos = db.query(models.Combo).filter(
            models.Combo.restaurante_id == restaurante_id,
            models.Combo.ativo == True,
        ).all()
        nested.commit()
        if combos:
            combos_linhas = []
            for c in combos:
                economia = c.preco_original - c.preco_combo
                combos_linhas.append(f"  🍽️ {c.nome} — R${c.preco_combo:.2f} (economia R${economia:.2f})")
            combos_texto = "\nCOMBOS:\n" + "\n".join(combos_linhas)
    except Exception:
        nested.rollback()
        logger.debug("Tabela combos não encontrada, ignorando")

    # Formas de pagamento
    pagamentos = []
    if site_config:
        if site_config.aceita_dinheiro:
            pagamentos.append("Dinheiro")
        if site_config.aceita_cartao:
            pagamentos.append("Cartão na entrega")
        if site_config.aceita_pix:
            pagamentos.append("Pix")
        if site_config.aceita_vale_refeicao:
            pagamentos.append("Vale Refeição")
    pagamento_texto = ", ".join(pagamentos) if pagamentos else "Dinheiro, Cartão, Pix"

    # Tempo entrega
    tempo_min = site_config.tempo_entrega_estimado if site_config else 50
    pedido_minimo = site_config.pedido_minimo if site_config else 0

    return f"""RESTAURANTE: {rest.nome_fantasia}
ENDEREÇO: {rest.endereco_completo or 'Não informado'}
HORÁRIO HOJE ({dia_semana}): {horario_texto} · {status_texto}
HORA ATUAL: {hora_atual}
TEMPO MÉDIO ENTREGA: {tempo_min} min
PEDIDO MÍNIMO: R${pedido_minimo:.2f}
FORMAS DE PAGAMENTO: {pagamento_texto}

CARDÁPIO DISPONÍVEL:
{cardapio_texto}
{promos_texto}
{combos_texto}"""


def build_client_context(
    db: Session,
    restaurante_id: int,
    telefone: str,
    conversa: Optional[models.BotConversa] = None,
    cliente: Optional[models.Cliente] = None,
) -> str:
    """Layer 3 — Contexto do cliente. Único por cliente, NUNCA cacheable."""
    if not cliente:
        # Buscar por telefone
        cliente = db.query(models.Cliente).filter(
            models.Cliente.restaurante_id == restaurante_id,
            models.Cliente.telefone.like(f"%{telefone[-8:]}"),
        ).first()

    if not cliente:
        return f"CLIENTE: Novo (telefone: {telefone})\nSem histórico. Perguntar nome e endereço naturalmente."

    # Endereço
    endereco_padrao = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.padrao == True,
        models.EnderecoCliente.ativo == True,
    ).first()

    # Últimos pedidos
    ultimos_pedidos = db.query(models.Pedido).filter(
        models.Pedido.cliente_id == cliente.id,
        models.Pedido.restaurante_id == restaurante_id,
    ).order_by(models.Pedido.data_criacao.desc()).limit(3).all()

    pedidos_texto = ""
    if ultimos_pedidos:
        linhas = []
        for p in ultimos_pedidos:
            data_str = p.data_criacao.strftime("%d/%m") if p.data_criacao else "?"
            linhas.append(f"  #{p.comanda} ({data_str}): {p.itens[:80]}... — R${p.valor_total:.2f} [{p.status}]")
        pedidos_texto = "\nÚLTIMOS PEDIDOS:\n" + "\n".join(linhas)

    # Pedido ativo
    pedido_ativo = db.query(models.Pedido).filter(
        models.Pedido.cliente_id == cliente.id,
        models.Pedido.restaurante_id == restaurante_id,
        models.Pedido.status.notin_(["entregue", "cancelado", "finalizado"]),
    ).order_by(models.Pedido.data_criacao.desc()).first()

    ativo_texto = ""
    if pedido_ativo:
        ativo_texto = f"\n⚡ PEDIDO ATIVO: #{pedido_ativo.comanda} — {pedido_ativo.status} — R${pedido_ativo.valor_total:.2f}"

    endereco_texto = ""
    if endereco_padrao:
        endereco_texto = f"\nENDEREÇO SALVO: {endereco_padrao.endereco_completo}"
        if endereco_padrao.complemento:
            endereco_texto += f", {endereco_padrao.complemento}"

    # Carrinho em construção
    carrinho_texto = ""
    if conversa and conversa.itens_carrinho:
        itens = conversa.itens_carrinho
        if itens:
            linhas = [f"  • {i.get('quantidade', 1)}x {i.get('nome', '?')} — R${i.get('subtotal', 0):.2f}" for i in itens]
            total = sum(i.get("subtotal", 0) for i in itens)
            carrinho_texto = f"\n🛒 CARRINHO ATUAL:\n" + "\n".join(linhas) + f"\n  Total parcial: R${total:.2f}"

    return f"""CLIENTE: {cliente.nome} (tel: {cliente.telefone})
CPF: {cliente.cpf or 'Não informado'}{endereco_texto}{pedidos_texto}{ativo_texto}{carrinho_texto}"""


def build_conversation_history(
    db: Session,
    conversa_id: int,
    limit: int = 20,
) -> list[dict]:
    """Monta histórico de mensagens para o LLM no formato [{role, content}]."""
    mensagens = db.query(models.BotMensagem).filter(
        models.BotMensagem.conversa_id == conversa_id,
    ).order_by(models.BotMensagem.criado_em.desc()).limit(limit).all()

    # Inverter para ordem cronológica
    mensagens = list(reversed(mensagens))

    history = []
    for m in mensagens:
        role = "assistant" if m.direcao == "enviada" else "user"
        content = m.conteudo or "[áudio sem transcrição]"
        history.append({"role": role, "content": content})

    return history
