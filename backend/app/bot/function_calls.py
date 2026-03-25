"""
Function Calls do Bot WhatsApp — 15 funções que o LLM pode chamar.
Cada função acessa o banco diretamente com restaurante_id (multi-tenant).
PEDIDOS SÃO CRIADOS SEM APROVAÇÃO HUMANA — vão direto para a cozinha.
"""
import json
import random
import string
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional

from .. import models

logger = logging.getLogger("superfood.bot.functions")


# ==================== DEFINIÇÕES DAS TOOLS (para xAI Grok) ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_cliente",
            "description": "Busca cliente pelo telefone. Retorna dados se encontrado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {"type": "string", "description": "Telefone do cliente"}
                },
                "required": ["telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cadastrar_cliente",
            "description": "Cadastra novo cliente. Usar quando cliente não encontrado e forneceu nome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do cliente"},
                    "telefone": {"type": "string", "description": "Telefone"},
                    "endereco": {"type": "string", "description": "Endereço completo de entrega"},
                    "bairro": {"type": "string", "description": "Bairro"},
                    "complemento": {"type": "string", "description": "Complemento (apto, casa, ref)"},
                },
                "required": ["nome", "telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_cardapio",
            "description": "Busca itens do cardápio por nome ou categoria. Use para confirmar preço e disponibilidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "busca": {"type": "string", "description": "Nome do produto ou categoria para buscar"},
                },
                "required": ["busca"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_categorias",
            "description": "Lista todas as categorias do cardápio disponíveis.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pedido",
            "description": "Cria pedido CONFIRMADO. SÓ chamar após cliente confirmar todos os itens, endereço e pagamento. Pedido vai DIRETO para a cozinha.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nome": {"type": "string"},
                    "cliente_telefone": {"type": "string"},
                    "itens": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "produto_id": {"type": "integer"},
                                "nome": {"type": "string"},
                                "quantidade": {"type": "integer"},
                                "preco_unitario": {"type": "number"},
                                "observacoes": {"type": "string"},
                            },
                            "required": ["produto_id", "nome", "quantidade", "preco_unitario"],
                        },
                    },
                    "endereco_entrega": {"type": "string"},
                    "forma_pagamento": {"type": "string", "enum": ["dinheiro", "cartao", "pix"]},
                    "troco_para": {"type": "number", "description": "Valor para troco (se dinheiro)"},
                    "tipo_entrega": {"type": "string", "enum": ["entrega", "retirada"]},
                    "observacoes": {"type": "string"},
                    "agendado_para": {"type": "string", "description": "ISO datetime se agendado"},
                },
                "required": ["cliente_nome", "cliente_telefone", "itens", "forma_pagamento", "tipo_entrega"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alterar_pedido",
            "description": "Altera itens de um pedido existente (adicionar/remover item, mudar observação). Só funciona se status permitir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer"},
                    "adicionar_itens": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "produto_id": {"type": "integer"},
                                "nome": {"type": "string"},
                                "quantidade": {"type": "integer"},
                                "preco_unitario": {"type": "number"},
                            },
                        },
                    },
                    "remover_item_ids": {"type": "array", "items": {"type": "integer"}},
                    "nova_observacao": {"type": "string"},
                },
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_pedido",
            "description": "Cancela um pedido. Só funciona se bot tem permissão e status permite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer"},
                    "motivo": {"type": "string"},
                },
                "required": ["pedido_id", "motivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repetir_ultimo_pedido",
            "description": "Repete o último pedido do cliente. Cliente diz 'quero o mesmo' ou 'repete o último'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_telefone": {"type": "string"},
                },
                "required": ["cliente_telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_status_pedido",
            "description": "Consulta status de um pedido específico ou do último pedido do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido (opcional se tiver telefone)"},
                    "cliente_telefone": {"type": "string", "description": "Telefone para buscar último pedido"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_horario",
            "description": "Verifica se restaurante está aberto e retorna horários.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_promocoes",
            "description": "Lista promoções e cupons ativos do restaurante.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_avaliacao",
            "description": "Registra avaliação do cliente sobre pedido/entrega.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer"},
                    "nota": {"type": "integer", "minimum": 1, "maximum": 5},
                    "categoria": {"type": "string", "enum": ["entrega", "comida", "atendimento"]},
                    "detalhe": {"type": "string"},
                },
                "required": ["pedido_id", "nota"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_problema",
            "description": "Registra problema/reclamação reportada pelo cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer"},
                    "tipo": {"type": "string", "enum": ["atraso", "item_errado", "item_faltando", "qualidade", "outro"]},
                    "descricao": {"type": "string"},
                },
                "required": ["tipo", "descricao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aplicar_cupom",
            "description": "Verifica e aplica cupom de desconto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo_cupom": {"type": "string"},
                    "valor_pedido": {"type": "number"},
                },
                "required": ["codigo_cupom", "valor_pedido"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalar_humano",
            "description": "Escala conversa para atendimento humano. Usar quando: cliente insiste em falar com humano, situação complexa, ou bot não consegue resolver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "motivo": {"type": "string"},
                },
                "required": ["motivo"],
            },
        },
    },
]


# ==================== EXECUÇÃO DAS FUNÇÕES ====================

def executar_funcao(
    nome: str,
    args: dict,
    db: Session,
    restaurante_id: int,
    bot_config: models.BotConfig,
    conversa: Optional[models.BotConversa] = None,
) -> str:
    """Executa uma function call e retorna resultado como string JSON."""
    try:
        if nome == "buscar_cliente":
            return _buscar_cliente(db, restaurante_id, args.get("telefone", ""))
        elif nome == "cadastrar_cliente":
            return _cadastrar_cliente(db, restaurante_id, args)
        elif nome == "buscar_cardapio":
            return _buscar_cardapio(db, restaurante_id, args.get("busca", ""))
        elif nome == "buscar_categorias":
            return _buscar_categorias(db, restaurante_id)
        elif nome == "criar_pedido":
            return _criar_pedido(db, restaurante_id, bot_config, args, conversa)
        elif nome == "alterar_pedido":
            return _alterar_pedido(db, restaurante_id, bot_config, args)
        elif nome == "cancelar_pedido":
            return _cancelar_pedido(db, restaurante_id, bot_config, args)
        elif nome == "repetir_ultimo_pedido":
            return _repetir_ultimo_pedido(db, restaurante_id, bot_config, args, conversa)
        elif nome == "consultar_status_pedido":
            return _consultar_status_pedido(db, restaurante_id, args)
        elif nome == "verificar_horario":
            return _verificar_horario(db, restaurante_id)
        elif nome == "buscar_promocoes":
            return _buscar_promocoes(db, restaurante_id)
        elif nome == "registrar_avaliacao":
            return _registrar_avaliacao(db, restaurante_id, args, conversa)
        elif nome == "registrar_problema":
            return _registrar_problema(db, restaurante_id, args, conversa)
        elif nome == "aplicar_cupom":
            return _aplicar_cupom(db, restaurante_id, args)
        elif nome == "escalar_humano":
            return _escalar_humano(db, restaurante_id, args, conversa)
        else:
            return json.dumps({"erro": f"Função desconhecida: {nome}"})
    except Exception as e:
        logger.error(f"Erro executando {nome}: {e}")
        return json.dumps({"erro": str(e)})


def _buscar_cliente(db: Session, restaurante_id: int, telefone: str) -> str:
    tel_limpo = "".join(c for c in telefone if c.isdigit())
    cliente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    if not cliente:
        return json.dumps({"encontrado": False, "mensagem": "Cliente não encontrado. Cadastrar novo?"})

    endereco = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.padrao == True,
    ).first()

    return json.dumps({
        "encontrado": True,
        "id": cliente.id,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "endereco": endereco.endereco_completo if endereco else None,
        "bairro": endereco.bairro if endereco else None,
        "complemento": endereco.complemento if endereco else None,
    })


def _cadastrar_cliente(db: Session, restaurante_id: int, args: dict) -> str:
    import hashlib
    nome = args.get("nome", "").strip()
    telefone = args.get("telefone", "").strip()

    if not nome or not telefone:
        return json.dumps({"erro": "Nome e telefone são obrigatórios"})

    # Verificar se já existe
    tel_limpo = "".join(c for c in telefone if c.isdigit())
    existente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    if existente:
        return json.dumps({"id": existente.id, "nome": existente.nome, "mensagem": "Cliente já cadastrado"})

    # Criar cliente
    senha_padrao = tel_limpo[:6] if len(tel_limpo) >= 6 else "123456"
    cliente = models.Cliente(
        restaurante_id=restaurante_id,
        nome=nome,
        telefone=tel_limpo,
        senha_hash=hashlib.sha256(senha_padrao.strip().encode()).hexdigest(),
    )
    db.add(cliente)
    db.flush()

    # Criar endereço se fornecido
    if args.get("endereco"):
        endereco = models.EnderecoCliente(
            cliente_id=cliente.id,
            endereco_completo=args["endereco"],
            bairro=args.get("bairro", ""),
            complemento=args.get("complemento", ""),
            padrao=True,
        )
        db.add(endereco)

    db.commit()
    return json.dumps({"id": cliente.id, "nome": nome, "mensagem": "Cliente cadastrado com sucesso"})


def _buscar_cardapio(db: Session, restaurante_id: int, busca: str) -> str:
    busca_lower = busca.lower()
    produtos = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante_id,
        models.Produto.disponivel == True,
        models.Produto.nome.ilike(f"%{busca_lower}%"),
    ).limit(10).all()

    if not produtos:
        # Tentar por categoria
        cat = db.query(models.CategoriaMenu).filter(
            models.CategoriaMenu.restaurante_id == restaurante_id,
            models.CategoriaMenu.nome.ilike(f"%{busca_lower}%"),
        ).first()

        if cat:
            produtos = db.query(models.Produto).filter(
                models.Produto.categoria_id == cat.id,
                models.Produto.disponivel == True,
            ).limit(10).all()

    if not produtos:
        return json.dumps({"encontrados": 0, "mensagem": f"Nenhum item encontrado para '{busca}'"})

    itens = []
    for p in produtos:
        preco = p.preco_promocional if p.promocao and p.preco_promocional else p.preco
        item = {"id": p.id, "nome": p.nome, "preco": preco, "descricao": p.descricao or ""}
        if p.promocao:
            item["preco_original"] = p.preco
            item["em_promocao"] = True
        # Variações
        variacoes = db.query(models.VariacaoProduto).filter(
            models.VariacaoProduto.produto_id == p.id,
            models.VariacaoProduto.ativo == True,
        ).all()
        if variacoes:
            item["variacoes"] = [{"id": v.id, "tipo": v.tipo_variacao, "nome": v.nome, "preco_extra": v.preco_adicional} for v in variacoes]
        itens.append(item)

    return json.dumps({"encontrados": len(itens), "itens": itens})


def _buscar_categorias(db: Session, restaurante_id: int) -> str:
    cats = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante_id,
        models.CategoriaMenu.ativo == True,
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    return json.dumps({
        "categorias": [{"id": c.id, "nome": c.nome, "descricao": c.descricao or ""} for c in cats]
    })


def _criar_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict, conversa: Optional[models.BotConversa]) -> str:
    """Cria pedido DIRETO — sem aprovação humana. Vai para cozinha automaticamente."""
    if not bot_config.pode_criar_pedido:
        return json.dumps({"erro": "Bot não tem permissão para criar pedidos"})

    itens = args.get("itens", [])
    if not itens:
        return json.dumps({"erro": "Nenhum item no pedido"})

    # Validar cada item contra o banco
    valor_total = 0
    itens_texto = []
    itens_detalhados = []

    for item in itens:
        produto = db.query(models.Produto).filter(
            models.Produto.id == item["produto_id"],
            models.Produto.restaurante_id == restaurante_id,
            models.Produto.disponivel == True,
        ).first()

        if not produto:
            return json.dumps({"erro": f"Produto '{item.get('nome', '?')}' não disponível"})

        preco_real = produto.preco_promocional if produto.promocao and produto.preco_promocional else produto.preco
        qtd = item.get("quantidade", 1)
        subtotal = preco_real * qtd
        valor_total += subtotal

        itens_texto.append(f"{qtd}x {produto.nome} (R${preco_real:.2f})")
        itens_detalhados.append({
            "produto_id": produto.id,
            "quantidade": qtd,
            "preco_unitario": preco_real,
            "observacoes": item.get("observacoes", ""),
        })

    # Buscar cliente
    tel = args.get("cliente_telefone", "")
    tel_limpo = "".join(c for c in tel if c.isdigit())
    cliente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    # Gerar comanda
    comanda = f"WA{random.randint(1000, 9999)}"

    # Calcular taxa de entrega
    taxa_entrega = 0
    tipo_entrega = args.get("tipo_entrega", "entrega")
    if tipo_entrega == "entrega":
        config = db.query(models.ConfigRestaurante).filter(
            models.ConfigRestaurante.restaurante_id == restaurante_id
        ).first()
        taxa_entrega = config.taxa_entrega_base if config else 5.0

    valor_total_final = valor_total + taxa_entrega

    # Criar pedido — STATUS: pendente → em_preparo se impressão automática
    status_inicial = "em_preparo" if bot_config.impressao_automatica_bot else "pendente"

    pedido = models.Pedido(
        restaurante_id=restaurante_id,
        cliente_id=cliente.id if cliente else None,
        comanda=comanda,
        tipo="delivery" if tipo_entrega == "entrega" else "retirada",
        origem="whatsapp_bot",
        tipo_entrega=tipo_entrega,
        cliente_nome=args.get("cliente_nome", cliente.nome if cliente else "Cliente WhatsApp"),
        cliente_telefone=tel_limpo,
        endereco_entrega=args.get("endereco_entrega", ""),
        itens=", ".join(itens_texto),
        carrinho_json=[{
            "produto_id": i["produto_id"],
            "nome": itens[idx].get("nome", ""),
            "quantidade": i["quantidade"],
            "preco_unitario": i["preco_unitario"],
            "subtotal": i["preco_unitario"] * i["quantidade"],
        } for idx, i in enumerate(itens_detalhados)],
        observacoes=args.get("observacoes", ""),
        valor_subtotal=valor_total,
        valor_taxa_entrega=taxa_entrega,
        valor_total=valor_total_final,
        forma_pagamento=args.get("forma_pagamento", "dinheiro"),
        troco_para=args.get("troco_para"),
        status=status_inicial,
        tipo_origem="whatsapp_bot",
        label_origem=f"WhatsApp - {args.get('cliente_nome', 'Cliente')}",
        agendado=bool(args.get("agendado_para")),
        historico_status=[{"status": status_inicial, "timestamp": datetime.utcnow().isoformat()}],
    )

    if args.get("agendado_para"):
        try:
            pedido.data_agendamento = datetime.fromisoformat(args["agendado_para"])
            pedido.status = "agendado"
        except (ValueError, TypeError):
            pass

    db.add(pedido)
    db.flush()

    # Criar itens detalhados
    for i in itens_detalhados:
        item_pedido = models.ItemPedido(
            pedido_id=pedido.id,
            produto_id=i["produto_id"],
            quantidade=i["quantidade"],
            preco_unitario=i["preco_unitario"],
            observacoes=i.get("observacoes", ""),
        )
        db.add(item_pedido)

    # Criar PedidoCozinha se KDS ativo e impressão automática
    config_cozinha = db.query(models.ConfigCozinha).filter(
        models.ConfigCozinha.restaurante_id == restaurante_id
    ).first()

    if config_cozinha and config_cozinha.kds_ativo and status_inicial == "em_preparo":
        pedido_cozinha = models.PedidoCozinha(
            restaurante_id=restaurante_id,
            pedido_id=pedido.id,
            status="NOVO",
        )
        db.add(pedido_cozinha)

    # Atualizar conversa
    if conversa:
        conversa.pedido_ativo_id = pedido.id
        conversa.itens_carrinho = None  # Limpar carrinho

    db.commit()

    logger.info(f"Pedido #{comanda} criado via WhatsApp Bot — restaurante={restaurante_id}, valor=R${valor_total_final:.2f}")

    return json.dumps({
        "sucesso": True,
        "pedido_id": pedido.id,
        "comanda": comanda,
        "status": status_inicial,
        "itens": itens_texto,
        "valor_subtotal": valor_total,
        "taxa_entrega": taxa_entrega,
        "valor_total": valor_total_final,
        "mensagem": f"Pedido #{comanda} criado! Valor: R${valor_total_final:.2f}. Status: {status_inicial}",
    })


def _alterar_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict) -> str:
    if not bot_config.pode_alterar_pedido:
        return json.dumps({"erro": "Bot não tem permissão para alterar pedidos"})

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == args["pedido_id"],
        models.Pedido.restaurante_id == restaurante_id,
    ).first()

    if not pedido:
        return json.dumps({"erro": "Pedido não encontrado"})

    # Verificar se status permite alteração
    status_permitidos = ["pendente", "em_preparo"]
    if pedido.status not in status_permitidos:
        return json.dumps({"erro": f"Pedido #{pedido.comanda} não pode ser alterado (status: {pedido.status})"})

    # Remover itens
    if args.get("remover_item_ids"):
        for item_id in args["remover_item_ids"]:
            item = db.query(models.ItemPedido).filter(
                models.ItemPedido.id == item_id,
                models.ItemPedido.pedido_id == pedido.id,
            ).first()
            if item:
                db.delete(item)

    # Adicionar itens
    if args.get("adicionar_itens"):
        for item_data in args["adicionar_itens"]:
            produto = db.query(models.Produto).filter(
                models.Produto.id == item_data["produto_id"],
                models.Produto.restaurante_id == restaurante_id,
            ).first()
            if produto:
                novo_item = models.ItemPedido(
                    pedido_id=pedido.id,
                    produto_id=produto.id,
                    quantidade=item_data.get("quantidade", 1),
                    preco_unitario=produto.preco_promocional if produto.promocao else produto.preco,
                )
                db.add(novo_item)

    # Atualizar observação
    if args.get("nova_observacao"):
        pedido.observacoes = args["nova_observacao"]

    # Recalcular total
    db.flush()
    itens = db.query(models.ItemPedido).filter(models.ItemPedido.pedido_id == pedido.id).all()
    valor_subtotal = sum(i.preco_unitario * i.quantidade for i in itens)
    pedido.valor_subtotal = valor_subtotal
    pedido.valor_total = valor_subtotal + (pedido.valor_taxa_entrega or 0)
    pedido.itens = ", ".join([f"{i.quantidade}x {db.query(models.Produto).get(i.produto_id).nome if i.produto_id else '?'}" for i in itens])

    db.commit()
    return json.dumps({"sucesso": True, "pedido_id": pedido.id, "novo_total": pedido.valor_total, "mensagem": f"Pedido #{pedido.comanda} alterado. Novo total: R${pedido.valor_total:.2f}"})


def _cancelar_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict) -> str:
    if not bot_config.pode_cancelar_pedido:
        return json.dumps({"erro": "Bot não tem permissão para cancelar pedidos. Vou chamar o responsável."})

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == args["pedido_id"],
        models.Pedido.restaurante_id == restaurante_id,
    ).first()

    if not pedido:
        return json.dumps({"erro": "Pedido não encontrado"})

    # Verificar status
    status_cancelavel = bot_config.cancelamento_ate_status or "em_preparo"
    status_ordem = ["pendente", "em_preparo", "pronto", "em_rota", "entregue"]
    try:
        idx_atual = status_ordem.index(pedido.status)
        idx_limite = status_ordem.index(status_cancelavel)
        if idx_atual > idx_limite:
            return json.dumps({"erro": f"Pedido #{pedido.comanda} não pode mais ser cancelado (status: {pedido.status})"})
    except ValueError:
        pass

    pedido.status = "cancelado"
    db.commit()

    return json.dumps({"sucesso": True, "mensagem": f"Pedido #{pedido.comanda} cancelado. Motivo: {args.get('motivo', 'Solicitado pelo cliente')}"})


def _repetir_ultimo_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict, conversa: Optional[models.BotConversa]) -> str:
    tel = args.get("cliente_telefone", "")
    tel_limpo = "".join(c for c in tel if c.isdigit())

    ultimo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == restaurante_id,
        models.Pedido.cliente_telefone.like(f"%{tel_limpo[-8:]}"),
        models.Pedido.status == "entregue",
    ).order_by(models.Pedido.data_criacao.desc()).first()

    if not ultimo:
        return json.dumps({"erro": "Nenhum pedido anterior encontrado"})

    # Verificar disponibilidade dos itens
    itens_repetir = []
    if ultimo.carrinho_json:
        for item in ultimo.carrinho_json:
            produto = db.query(models.Produto).filter(
                models.Produto.id == item.get("produto_id"),
                models.Produto.disponivel == True,
            ).first()
            if produto:
                preco_atual = produto.preco_promocional if produto.promocao else produto.preco
                itens_repetir.append({
                    "produto_id": produto.id,
                    "nome": produto.nome,
                    "quantidade": item.get("quantidade", 1),
                    "preco_unitario": preco_atual,
                })

    if not itens_repetir:
        return json.dumps({"erro": "Itens do último pedido não estão mais disponíveis"})

    valor_total = sum(i["preco_unitario"] * i["quantidade"] for i in itens_repetir)
    itens_texto = [f"{i['quantidade']}x {i['nome']} (R${i['preco_unitario']:.2f})" for i in itens_repetir]

    return json.dumps({
        "ultimo_pedido": {
            "comanda": ultimo.comanda,
            "itens": itens_texto,
            "endereco": ultimo.endereco_entrega,
            "valor_estimado": valor_total,
        },
        "mensagem": f"Último pedido: {', '.join(itens_texto)}. Total: R${valor_total:.2f}. Confirma? Mesmo endereço?",
        "itens_para_criar": itens_repetir,
    })


def _consultar_status_pedido(db: Session, restaurante_id: int, args: dict) -> str:
    pedido = None
    if args.get("pedido_id"):
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == args["pedido_id"],
            models.Pedido.restaurante_id == restaurante_id,
        ).first()
    elif args.get("cliente_telefone"):
        tel = "".join(c for c in args["cliente_telefone"] if c.isdigit())
        pedido = db.query(models.Pedido).filter(
            models.Pedido.restaurante_id == restaurante_id,
            models.Pedido.cliente_telefone.like(f"%{tel[-8:]}"),
        ).order_by(models.Pedido.data_criacao.desc()).first()

    if not pedido:
        return json.dumps({"erro": "Nenhum pedido encontrado"})

    status_map = {
        "pendente": "Recebido, aguardando confirmação",
        "em_preparo": "Sendo preparado na cozinha 👨‍🍳",
        "pronto": "Pronto! Aguardando entregador 📦",
        "em_rota": "A caminho do seu endereço 🛵",
        "entregue": "Entregue ✅",
        "cancelado": "Cancelado ❌",
        "agendado": "Agendado para entrega futura 📅",
    }

    return json.dumps({
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "status_texto": status_map.get(pedido.status, pedido.status),
        "valor_total": pedido.valor_total,
        "itens": pedido.itens,
        "criado_em": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
    })


def _verificar_horario(db: Session, restaurante_id: int) -> str:
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    if not config:
        return json.dumps({"erro": "Configuração não encontrada"})

    agora = datetime.utcnow() - timedelta(hours=3)
    hora_atual = agora.strftime("%H:%M")
    dia = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"][agora.weekday()]

    dias_abertos = (config.dias_semana_abertos or "").split(",")
    abertura = config.horario_abertura or "18:00"
    fechamento = config.horario_fechamento or "23:00"

    aberto = dia in dias_abertos and abertura <= hora_atual <= fechamento

    return json.dumps({
        "aberto": aberto,
        "hora_atual": hora_atual,
        "dia_semana": dia,
        "horario": f"{abertura} às {fechamento}",
        "dias_abertos": dias_abertos,
    })


def _buscar_promocoes(db: Session, restaurante_id: int) -> str:
    promos = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante_id,
        models.Promocao.ativo == True,
    ).all()

    combos = db.query(models.Combo).filter(
        models.Combo.restaurante_id == restaurante_id,
        models.Combo.ativo == True,
    ).all()

    result = {"promocoes": [], "combos": []}
    for p in promos:
        result["promocoes"].append({
            "nome": p.nome,
            "tipo": p.tipo_desconto,
            "valor": p.valor_desconto,
            "cupom": p.codigo_cupom,
            "minimo": p.valor_pedido_minimo,
        })
    for c in combos:
        result["combos"].append({
            "nome": c.nome,
            "preco": c.preco_combo,
            "economia": c.preco_original - c.preco_combo,
        })

    return json.dumps(result)


def _registrar_avaliacao(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    avaliacao = models.BotAvaliacao(
        restaurante_id=restaurante_id,
        pedido_id=args.get("pedido_id"),
        cliente_id=conversa.cliente_id if conversa else None,
        conversa_id=conversa.id if conversa else None,
        nota=args["nota"],
        categoria=args.get("categoria"),
        detalhe=args.get("detalhe"),
        status="respondida",
        respondido_em=datetime.utcnow(),
    )
    db.add(avaliacao)
    db.commit()

    nota = args["nota"]
    if nota >= 4:
        return json.dumps({"sucesso": True, "nota": nota, "mensagem": "Obrigado pela avaliação! 😊 Se puder, avalie a gente no Google Maps também!"})
    else:
        return json.dumps({"sucesso": True, "nota": nota, "mensagem": "Sentimos muito pela experiência. Já registrei o problema e o responsável vai entrar em contato."})


def _registrar_problema(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    problema = models.BotProblema(
        restaurante_id=restaurante_id,
        pedido_id=args.get("pedido_id"),
        cliente_id=conversa.cliente_id if conversa else None,
        conversa_id=conversa.id if conversa else None,
        tipo=args["tipo"],
        descricao=args["descricao"],
    )
    db.add(problema)
    db.commit()

    return json.dumps({"sucesso": True, "problema_id": problema.id, "mensagem": "Problema registrado. O responsável será notificado imediatamente."})


def _aplicar_cupom(db: Session, restaurante_id: int, args: dict) -> str:
    cupom = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante_id,
        models.Promocao.codigo_cupom == args["codigo_cupom"].upper(),
        models.Promocao.ativo == True,
    ).first()

    if not cupom:
        return json.dumps({"valido": False, "mensagem": "Cupom inválido ou expirado"})

    if cupom.uso_limitado and cupom.usos_realizados >= (cupom.limite_usos or 0):
        return json.dumps({"valido": False, "mensagem": "Cupom esgotado"})

    valor_pedido = args.get("valor_pedido", 0)
    if cupom.valor_pedido_minimo and valor_pedido < cupom.valor_pedido_minimo:
        return json.dumps({"valido": False, "mensagem": f"Pedido mínimo R${cupom.valor_pedido_minimo:.2f} para este cupom"})

    if cupom.tipo_desconto == "percentual":
        desconto = valor_pedido * (cupom.valor_desconto / 100)
        if cupom.desconto_maximo:
            desconto = min(desconto, cupom.desconto_maximo)
    else:
        desconto = cupom.valor_desconto

    return json.dumps({
        "valido": True,
        "desconto": desconto,
        "novo_total": valor_pedido - desconto,
        "mensagem": f"Cupom aplicado! Desconto: R${desconto:.2f}",
    })


def _escalar_humano(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    if conversa:
        conversa.status = "handoff"
        conversa.handoff_em = datetime.utcnow()
        conversa.handoff_motivo = args.get("motivo", "Solicitado pelo cliente")
        db.commit()

    return json.dumps({
        "sucesso": True,
        "mensagem": "Conversa transferida para atendimento humano. O responsável será notificado.",
    })
