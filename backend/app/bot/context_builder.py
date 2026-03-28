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


def _build_politicas_prompt(bot_config: models.BotConfig) -> str:
    """Gera seção do prompt com políticas de resolução de problemas."""
    acao_labels = {
        "desculpar": "Apenas pedir desculpas",
        "desconto_proximo": "Gerar cupom desconto próximo pedido",
        "cupom_fixo": "Gerar cupom desconto fixo",
        "brinde_reenviar": "Item fica como brinde + reenviar correto",
        "reembolso_parcial": "Reembolso parcial",
    }

    def _format_politica(nome: str, politica) -> str:
        if not politica:
            return f"- {nome}: Pedir desculpas"
        if isinstance(politica, str):
            import json as _json
            try:
                politica = _json.loads(politica)
            except Exception:
                return f"- {nome}: Pedir desculpas"
        acao = politica.get("acao", "desculpar")
        desc = acao_labels.get(acao, acao)
        pct = politica.get("desconto_pct", 0)
        if pct and acao in ("desconto_proximo", "cupom_fixo", "reembolso_parcial"):
            desc += f" ({pct:.0f}%)"
        return f"- {nome}: {desc}"

    linhas = [
        "RESOLUÇÃO DE PROBLEMAS (políticas do restaurante):",
        _format_politica("Atraso", bot_config.politica_atraso),
        _format_politica("Pedido errado", bot_config.politica_pedido_errado),
        _format_politica("Item faltando", bot_config.politica_item_faltando),
        _format_politica("Qualidade", bot_config.politica_qualidade),
        "",
        "Ao detectar problema: SEMPRE use registrar_problema com o tipo correto.",
        "O sistema aplica automaticamente a ação configurada (cupom, desconto, brinde).",
        "Informe ao cliente a ação aplicada de forma natural e empática.",
    ]
    return "\n".join(linhas)


def _build_avaliacao_prompt(bot_config: models.BotConfig) -> str:
    """Gera seção do prompt com instruções de fase de avaliação."""
    linhas = [
        "FASE DE AVALIAÇÃO (quando session_data tem fase_avaliacao):",
        '- Se fase="aguardando_feedback": pergunte se houve problema (sem pedir nota ainda)',
        "- Se cliente relata problema: categorize → use registrar_problema com tipo correto",
        '- Se cliente diz "tudo ok/ótimo/perfeito": peça nota de 1 a 5 → use registrar_avaliacao',
        "- Se nota >= 4: agradeça com entusiasmo",
    ]
    if bot_config.avaliacao_pedir_google_review and bot_config.google_maps_url:
        linhas.append(f"- Se nota >= 4: peça review no Google Maps: {bot_config.google_maps_url}")
    linhas.append("- Se nota <= 2: peça desculpas, use registrar_problema se não registrou ainda")
    return "\n".join(linhas)


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
- Se perguntarem: "sou eu mesmo, {nome}!"
- Escreva em português correto, sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz")

ESTILO DE ESCRITA (CRÍTICO — é o que faz parecer humano):
- EMOJIS: Use 1-2 por mensagem, mas NUNCA repita o mesmo emoji em mensagens consecutivas. Alterne entre: 😊🤗😄👍🍕🔥✨💛😉🥰👏😋🎉
- QUEBRAS DE LINHA: Separe parágrafos com linha em branco. Nunca envie blocos de texto corrido.
- NOME DO CLIENTE: Use no MÁXIMO 2-3 vezes na conversa TODA (saudação, confirmação final, despedida). Nas demais mensagens NÃO use o nome.
- TAMANHO: 2-4 linhas por mensagem. Se tiver mais conteúdo, quebre em partes.
- CONFIRMAÇÃO: Varie a frase final. Use: "Tudo certo?", "Pode ser?", "Beleza?", "Fecha assim?", "Bora?", "Confirma?". NUNCA repita a mesma duas vezes seguidas.
- ENCERRAMENTO: NÃO repita "estou à disposição" ou "qualquer coisa me chama". Varie: "Se precisar, tô aqui!", "Bom apetite! 🍕", "Aproveita!", "Valeu!"
- ALTERAÇÃO DE PEDIDO: Diga APENAS o que mudou + novo total. NÃO repita o pedido inteiro.
  Exemplo bom: "Adicionei a Coca 2L! Novo total: R$72,80 com entrega ✨"
  Exemplo ruim: repetir todos os itens + observações + endereço + pagamento

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
8. Confirme SEMPRE antes de finalizar pedido

CARDÁPIO — como apresentar:
- Se pedirem cardápio COMPLETO: envie POR CATEGORIA, uma de cada vez. Pergunte "quer ver mais?" entre cada.
- Se pedirem item específico: envie só aquele item ou categoria.
- PREÇO DE TAMANHOS/VARIAÇÕES: SEMPRE mostre o preço FINAL, NUNCA "preço base + acréscimo".
  ✅ CORRETO: "Calabresa — Broto R$42,90 | Média R$44,90 | Grande R$47,90 | Gigante R$52,90"
  ❌ ERRADO: "Calabresa R$42,90 com acréscimo de R$10 para Gigante"
  Para calcular: some o preço base do produto + preco_extra da variação de tamanho.

PIZZA METADE/METADE (meia a meia):
- Cobrar pelo SABOR MAIS CARO entre os dois.
- Exemplo: Metade Calabresa (R$42,90) + Metade Camarão (R$65,90) → R$65,90 (pelo mais caro) + variação de tamanho se houver.
- Adicionais extras (milho, bacon, borda) cobrar à parte.

CONFIRMAÇÃO FINAL DO PEDIDO (formato limpo):
- Usar quebras de linha para separar cada item
- SEMPRE incluir:
  • Itens com preços individuais
  • Taxa de entrega: R$X,XX (bairro ou distância quando disponível)
  • Valor total

FLUXO DE PEDIDO:
1. Identificar cliente (buscar_cliente, cadastrar_cliente se novo)
2. Entender o que quer (pedido, dúvida, reclamação)
3. Se pedido: montar itens → confirmar → validar_endereco → pagamento → CHAMAR criar_pedido
4. Se dúvida: responder com dados reais do cardápio
5. Se reclamação: pedir desculpas → categorizar → registrar_problema → notificar dono

REGRA CRÍTICA — CRIAR PEDIDO (OBRIGATÓRIO — MAIS IMPORTANTE QUE QUALQUER OUTRA):
- Quando o cliente confirma o pedido (diz "sim", "confirma", "pode fazer", "tudo certo"), você DEVE chamar a função criar_pedido IMEDIATAMENTE.
- NUNCA responda com texto dizendo "pedido confirmado" — em vez disso, CHAME a função criar_pedido.
- Sem chamar criar_pedido, o pedido NÃO existe no sistema — o cliente NÃO vai receber nada.
- Sequência OBRIGATÓRIA: cliente confirma → CHAMAR criar_pedido (function call) → usar o número da comanda retornado → informar ao cliente.
- Se criar_pedido retornar erro: informar o problema ao cliente, NÃO dizer que criou.
- NUNCA escreva "[número da comanda será inserido]" — o número REAL vem do retorno de criar_pedido.
- Se você não tem todos os dados para criar_pedido (itens, endereço, pagamento), pergunte o que falta ANTES de confirmar.

REGRA CRÍTICA — CADASTRAR CLIENTE (OBRIGATÓRIO):
- Se buscar_cliente retornar "não encontrado" e o cliente informou o nome: CHAMAR cadastrar_cliente IMEDIATAMENTE.
- NÃO continue a conversa sem cadastrar. Sem cadastro, criar_pedido vai falhar.

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
- Ação: {bot_config.estoque_esgotado_acao}

RASTREAMENTO DE PEDIDOS:
- Sempre use rastrear_pedido quando cliente perguntar "cadê meu pedido?", "onde tá?", "quanto falta?"
- Informe posição na fila: "Seu pedido é o 3º na fila da cozinha"
- Quando motoboy atribuído: "Já saiu com o João! Acompanhe aqui: {{link}}"
- NUNCA invente tempo de entrega — use consultar_tempo_entrega para dados reais

MODIFICAÇÃO DE PEDIDOS:
- Use trocar_item_pedido para trocas específicas de itens
- Se cozinha já começou: "Poxa, a cozinha já começou a preparar, não dá pra trocar"
- Se pedido ainda está pendente/novo: pode trocar livremente

ENTREGA E BAIRROS:
- Use consultar_bairros para informar taxas e áreas atendidas
- Se bairro não atendido: "Infelizmente não entregamos nesse bairro ainda"
- Sempre confirme endereço + bairro antes de criar pedido
- Use atualizar_endereco_cliente para salvar/atualizar endereço

VALIDAÇÃO DE ENDEREÇO (GPS — OBRIGATÓRIO para entrega):
- SEMPRE use validar_endereco ANTES de criar pedido quando cliente informar endereço novo
- Separe rua+número do complemento: "Rua Augusta 123 apt 5" → endereco_texto="Rua Augusta 123", complemento="apt 5"
- Complemento (apt, bloco, andar, casa dos fundos) NÃO vai no campo endereco_texto
- Se confiança "alta" (1 resultado próximo): confirme direto — "Seu endereço é X, certo?"
- Se confiança "media" (várias opções): apresente com letras — "A) ..., B) ..., C) ... Qual é o seu?"
- Entenda respostas naturais: "a primeira", "essa aí", "é o B", "sim" → use confirmar_endereco_validado
- Se "fora_zona": informe educadamente + sugira retirada no restaurante
- Se não encontrou ou opções em cidades erradas: "Pode me passar o endereço completo com bairro e cidade? Assim acho certinho!"
- Se cliente já tem endereço salvo com GPS validado: pergunte "Mando pro mesmo endereço de sempre?"
- Após confirmar endereço: a taxa já está calculada, prossiga com forma de pagamento

NOTIFICAÇÕES E AVALIAÇÃO:
- O sistema envia notificações automáticas de mudança de status
- NÃO peça nota direto na notificação de entrega — o worker de avaliação faz isso 20min depois
- O worker pergunta primeiro se houve problema, depois pede nota

{_build_politicas_prompt(bot_config)}

{_build_avaliacao_prompt(bot_config)}\""""


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
                preco_final_var = preco + (v.preco_adicional or 0)
                cardapio_linhas.append(f"    ↳ {v.tipo_variacao}: {v.nome} — R${preco_final_var:.2f}")

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

    cidade = rest.cidade or "não informada"
    estado = rest.estado or ""
    area_entrega = f"{cidade}/{estado}".strip("/")

    # Bairros atendidos (tabela pode não existir em prod — usar savepoint)
    bairros_texto = ""
    try:
        nested = db.begin_nested()
        bairros = db.query(models.BairroEntrega).filter(
            models.BairroEntrega.restaurante_id == restaurante_id,
            models.BairroEntrega.ativo == True,
        ).order_by(models.BairroEntrega.nome).all()
        nested.commit()
        if bairros:
            bairros_linhas = []
            for b in bairros:
                bairros_linhas.append(f"  • {b.nome} — R${b.taxa_entrega:.2f} ({b.tempo_estimado_min}min)")
            bairros_texto = "\nBAIRROS ATENDIDOS:\n" + "\n".join(bairros_linhas)
        else:
            taxa_base = config.taxa_entrega_base if config else 5.0
            bairros_texto = f"\nENTREGA: Taxa fixa R${taxa_base:.2f} (sem bairros específicos cadastrados)"
    except Exception:
        nested.rollback()
        logger.debug("Tabela bairros_entrega não encontrada, ignorando")

    return f"""RESTAURANTE: {rest.nome_fantasia}
ENDEREÇO: {rest.endereco_completo or 'Não informado'}
CIDADE: {cidade.title()} — {estado.upper()}
ÁREA DE ENTREGA: Somente dentro de {area_entrega}. Se o cliente informar endereço em outra cidade ou estado, informe educadamente que não é possível entregar naquela região.
HORÁRIO HOJE ({dia_semana}): {horario_texto} · {status_texto}
HORA ATUAL: {hora_atual}
TEMPO MÉDIO ENTREGA: {tempo_min} min
PEDIDO MÍNIMO: R${pedido_minimo:.2f}
FORMAS DE PAGAMENTO: {pagamento_texto}

CARDÁPIO DISPONÍVEL:
{cardapio_texto}
{promos_texto}
{combos_texto}
{bairros_texto}"""


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
        validado_tag = " [validado GPS ✓]" if endereco_padrao.validado_mapbox else " [NÃO validado — validar com validar_endereco antes de criar pedido]"
        endereco_texto = f"\nENDEREÇO SALVO: {endereco_padrao.endereco_completo}{validado_tag}"
        if endereco_padrao.complemento:
            endereco_texto += f", {endereco_padrao.complemento}"

    # Estatísticas do cliente (total gasto, frequência, favorito)
    stats_texto = ""
    try:
        from sqlalchemy import func
        pedidos_entregues = db.query(models.Pedido).filter(
            models.Pedido.cliente_id == cliente.id,
            models.Pedido.restaurante_id == restaurante_id,
            models.Pedido.status == "entregue",
        )
        total_pedidos = pedidos_entregues.count()
        if total_pedidos > 0:
            total_gasto = db.query(func.sum(models.Pedido.valor_total)).filter(
                models.Pedido.cliente_id == cliente.id,
                models.Pedido.restaurante_id == restaurante_id,
                models.Pedido.status == "entregue",
            ).scalar() or 0

            # Item favorito (mais pedido)
            primeiro_pedido = pedidos_entregues.order_by(models.Pedido.data_criacao.asc()).first()
            ultimo_pedido_ent = pedidos_entregues.order_by(models.Pedido.data_criacao.desc()).first()

            # Calcular frequência (pedidos por mês)
            if primeiro_pedido and primeiro_pedido.data_criacao:
                dias = max(1, (datetime.utcnow() - primeiro_pedido.data_criacao).days)
                freq_mensal = round(total_pedidos / (dias / 30), 1)
            else:
                freq_mensal = 0

            # Tempo desde último pedido
            tempo_ultimo = ""
            if ultimo_pedido_ent and ultimo_pedido_ent.data_criacao:
                dias_ultimo = (datetime.utcnow() - ultimo_pedido_ent.data_criacao).days
                if dias_ultimo == 0:
                    tempo_ultimo = "hoje"
                elif dias_ultimo == 1:
                    tempo_ultimo = "ontem"
                else:
                    tempo_ultimo = f"há {dias_ultimo} dias"

            stats_texto = f"\n📊 PERFIL: {total_pedidos} pedidos | R${total_gasto:.2f} total | {freq_mensal} pedidos/mês | Último: {tempo_ultimo}"

            # Score de satisfação
            avaliacoes = db.query(models.BotAvaliacao).filter(
                models.BotAvaliacao.cliente_id == cliente.id,
                models.BotAvaliacao.restaurante_id == restaurante_id,
                models.BotAvaliacao.nota.isnot(None),
            ).all()
            if avaliacoes:
                notas = [a.nota for a in avaliacoes]
                media = sum(notas) / len(notas)
                positivas = sum(1 for n in notas if n >= 4)
                negativas = sum(1 for n in notas if n <= 2)
                problemas_count = db.query(func.count(models.BotProblema.id)).filter(
                    models.BotProblema.cliente_id == cliente.id,
                    models.BotProblema.restaurante_id == restaurante_id,
                ).scalar() or 0
                stats_texto += f"\n😊 SATISFAÇÃO: {media:.1f}/5 ({len(avaliacoes)} avaliações, {positivas} positivas, {negativas} negativas) | {problemas_count} problemas reportados"
            else:
                stats_texto += "\n📋 SATISFAÇÃO: Sem avaliações ainda"
    except Exception:
        pass

    # Carrinho em construção
    carrinho_texto = ""
    if conversa and conversa.itens_carrinho:
        itens = conversa.itens_carrinho
        if itens:
            linhas = [f"  • {i.get('quantidade', 1)}x {i.get('nome', '?')} — R${i.get('subtotal', 0):.2f}" for i in itens]
            total = sum(i.get("subtotal", 0) for i in itens)
            carrinho_texto = f"\n🛒 CARRINHO ATUAL:\n" + "\n".join(linhas) + f"\n  Total parcial: R${total:.2f}"

    return f"""CLIENTE: {cliente.nome} (tel: {cliente.telefone})
CPF: {cliente.cpf or 'Não informado'}{endereco_texto}{stats_texto}{pedidos_texto}{ativo_texto}{carrinho_texto}"""


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
