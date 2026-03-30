"""
Function Calls do Bot WhatsApp — funções que o LLM pode chamar.
Cada função acessa o banco diretamente com restaurante_id (multi-tenant).
PEDIDOS SÃO CRIADOS SEM APROVAÇÃO HUMANA — vão direto para a cozinha.
Pix Online: quando forma_pagamento='pix' e restaurante tem PixConfig ativo,
o pedido fica pendente e gera link de pagamento automaticamente.
"""
import json
import random
import string
import logging
import inspect
import unicodedata
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional

from .. import models
from ..email_service import BASE_URL

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
            "description": "Cadastra novo cliente IMEDIATAMENTE quando buscar_cliente retorna 'não encontrado' e o cliente informou o nome. NÃO espere pelo endereço — cadastre só com nome + telefone. Endereço pode ser adicionado depois.",
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
                    "forma_pagamento": {"type": "string", "enum": ["dinheiro", "cartao", "pix", "pix_online", "vale_refeicao"], "description": "dinheiro, cartao, pix (na entrega), pix_online (link pagamento), vale_refeicao"},
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
    {
        "type": "function",
        "function": {
            "name": "rastrear_pedido",
            "description": "Rastreia pedido em tempo real: status detalhado, posição na fila da cozinha, motoboy atribuído com GPS, ETA e link de acompanhamento. Use quando cliente perguntar 'cadê meu pedido', 'onde tá', 'quanto falta'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido (opcional se tiver telefone)"},
                    "telefone": {"type": "string", "description": "Telefone do cliente para buscar pedido ativo"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trocar_item_pedido",
            "description": "Troca um item do pedido por outro do cardápio. Respeita status da cozinha — se já começou a preparar, rejeita.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido"},
                    "item_remover": {"type": "string", "description": "Nome do item a remover"},
                    "item_novo": {"type": "string", "description": "Nome do novo item"},
                    "quantidade": {"type": "integer", "description": "Quantidade do novo item", "default": 1},
                },
                "required": ["pedido_id", "item_remover", "item_novo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tempo_entrega",
            "description": "Consulta tempo estimado de preparo + entrega com base na fila real da cozinha e bairro. Use para informar ao cliente quanto tempo vai demorar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bairro": {"type": "string", "description": "Bairro do cliente (opcional, para calcular taxa e tempo extra)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_bairros",
            "description": "Lista bairros atendidos pelo restaurante com taxas de entrega e tempo estimado. Use quando cliente perguntar sobre entrega, taxa ou área atendida.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_bairro": {"type": "string", "description": "Filtro parcial por nome do bairro (opcional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "atualizar_endereco_cliente",
            "description": "Atualiza ou cadastra endereço de entrega do cliente. Valida se bairro está na área de entrega.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {"type": "string", "description": "Telefone do cliente"},
                    "endereco_completo": {"type": "string", "description": "Endereço completo (rua, número)"},
                    "complemento": {"type": "string", "description": "Complemento (apto, bloco, referência)"},
                    "bairro": {"type": "string", "description": "Bairro"},
                    "referencia": {"type": "string", "description": "Ponto de referência"},
                },
                "required": ["telefone", "endereco_completo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validar_endereco",
            "description": "SEMPRE chamar ANTES de criar pedido quando cliente informar endereço novo ou diferente do salvo. Valida endereço via GPS (Mapbox) e calcula taxa de entrega real por distância. Separe rua+número do complemento (apt, bloco, andar — complemento NÃO vai na busca).",
            "parameters": {
                "type": "object",
                "properties": {
                    "endereco_texto": {"type": "string", "description": "Rua + número (ex: 'Rua Augusta 123'). NÃO incluir complemento aqui."},
                    "complemento": {"type": "string", "description": "Complemento separado: apt, bloco, andar, casa dos fundos, etc."},
                    "referencia": {"type": "string", "description": "Ponto de referência (ex: 'perto do mercado')"},
                },
                "required": ["endereco_texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirmar_endereco_validado",
            "description": "Chamar DEPOIS que cliente escolheu/confirmou uma das sugestões retornadas por validar_endereco. Salva endereço com coordenadas GPS no cadastro do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {"type": "string", "description": "Telefone do cliente"},
                    "opcao_index": {"type": "integer", "description": "Índice da opção escolhida (0=A, 1=B, 2=C)"},
                    "complemento": {"type": "string", "description": "Complemento (apt, bloco, referência)"},
                    "referencia": {"type": "string", "description": "Ponto de referência"},
                },
                "required": ["telefone", "opcao_index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_cobranca_pix",
            "description": "Gera nova cobrança Pix Online para um pedido (caso a anterior tenha expirado). Retorna link de pagamento e código Pix copia-e-cola.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido"},
                },
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pagamento_pix",
            "description": "Consulta se o pagamento Pix de um pedido foi confirmado. Retorna status da cobrança.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido"},
                },
                "required": ["pedido_id"],
            },
        },
    },
]


# ==================== EXECUÇÃO DAS FUNÇÕES ====================

async def executar_funcao(
    nome: str,
    args: dict,
    db: Session,
    restaurante_id: int,
    bot_config: models.BotConfig,
    conversa: Optional[models.BotConversa] = None,
) -> str:
    """Executa uma function call e retorna resultado como string JSON.

    Usa savepoint (begin_nested) para isolar erros de BD —
    se a função falhar, só o savepoint é revertido, preservando
    a transação principal (conversa, msg_recebida, etc.).

    Suporta funções sync e async (criar_pedido, gerar_cobranca_pix, etc.).
    """
    savepoint = None
    try:
        savepoint = db.begin_nested()

        if nome == "buscar_cliente":
            result = _buscar_cliente(db, restaurante_id, args.get("telefone", ""))
        elif nome == "cadastrar_cliente":
            result = _cadastrar_cliente(db, restaurante_id, args)
        elif nome == "buscar_cardapio":
            result = _buscar_cardapio(db, restaurante_id, args.get("busca", ""))
        elif nome == "buscar_categorias":
            result = _buscar_categorias(db, restaurante_id)
        elif nome == "criar_pedido":
            result = await _criar_pedido(db, restaurante_id, bot_config, args, conversa)
        elif nome == "alterar_pedido":
            result = _alterar_pedido(db, restaurante_id, bot_config, args)
        elif nome == "cancelar_pedido":
            result = _cancelar_pedido(db, restaurante_id, bot_config, args)
        elif nome == "repetir_ultimo_pedido":
            result = _repetir_ultimo_pedido(db, restaurante_id, bot_config, args, conversa)
        elif nome == "consultar_status_pedido":
            result = _consultar_status_pedido(db, restaurante_id, args)
        elif nome == "verificar_horario":
            result = _verificar_horario(db, restaurante_id)
        elif nome == "buscar_promocoes":
            result = _buscar_promocoes(db, restaurante_id, conversa)
        elif nome == "registrar_avaliacao":
            result = _registrar_avaliacao(db, restaurante_id, args, conversa)
        elif nome == "registrar_problema":
            result = _registrar_problema(db, restaurante_id, args, conversa)
        elif nome == "aplicar_cupom":
            result = _aplicar_cupom(db, restaurante_id, args, conversa)
        elif nome == "escalar_humano":
            result = _escalar_humano(db, restaurante_id, args, conversa)
        elif nome == "rastrear_pedido":
            result = _rastrear_pedido(db, restaurante_id, args)
        elif nome == "trocar_item_pedido":
            result = _trocar_item_pedido(db, restaurante_id, bot_config, args)
        elif nome == "consultar_tempo_entrega":
            result = _consultar_tempo_entrega(db, restaurante_id, args)
        elif nome == "consultar_bairros":
            result = _consultar_bairros(db, restaurante_id, args)
        elif nome == "atualizar_endereco_cliente":
            result = _atualizar_endereco_cliente(db, restaurante_id, args)
        elif nome == "validar_endereco":
            result = _validar_endereco(db, restaurante_id, args, conversa)
        elif nome == "confirmar_endereco_validado":
            result = _confirmar_endereco_validado(db, restaurante_id, args, conversa)
        elif nome == "gerar_cobranca_pix":
            result = await _gerar_cobranca_pix(db, restaurante_id, args)
        elif nome == "consultar_pagamento_pix":
            result = _consultar_pagamento_pix(db, restaurante_id, args)
        else:
            result = json.dumps({"erro": f"Função desconhecida: {nome}"})

        return result
    except Exception as e:
        logger.error(f"Erro executando {nome}: {e}", exc_info=True)
        # Rollback apenas do savepoint — preserva transação principal
        try:
            if savepoint:
                savepoint.rollback()
            else:
                db.rollback()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return json.dumps({"erro": str(e)})


def _buscar_cliente(db: Session, restaurante_id: int, telefone: str) -> str:
    tel_limpo = "".join(c for c in telefone if c.isdigit())
    cliente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    if not cliente:
        return json.dumps({
            "encontrado": False,
            "telefone": tel_limpo,
            "mensagem": "Cliente não encontrado. OBRIGATÓRIO: pergunte o nome e chame cadastrar_cliente(nome, telefone) IMEDIATAMENTE. NÃO espere pelo endereço.",
        })

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


async def _criar_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict, conversa: Optional[models.BotConversa]) -> str:
    """Cria pedido DIRETO — sem aprovação humana. Vai para cozinha automaticamente.
    Se forma_pagamento='pix' e Pix Online ativo: pedido fica pendente + gera link pagamento."""
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
    restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if tipo_entrega == "entrega":
        # Prioridade 1: Usar taxa pré-calculada pelo Mapbox (validar_endereco)
        endereco_validado = None
        if conversa and conversa.session_data:
            endereco_validado = conversa.session_data.get("endereco_validado")
        if endereco_validado:
            taxa_entrega = endereco_validado.get("taxa_entrega", 0)
            if not args.get("endereco_entrega"):
                args["endereco_entrega"] = endereco_validado.get("place_name", "")
        else:
            # Prioridade 2: Fallback — lógica por bairro (original)
            endereco_entrega = args.get("endereco_entrega", "").lower()
            cidade_rest = (restaurante.cidade or "").lower().strip()
            if cidade_rest and endereco_entrega and cidade_rest not in endereco_entrega:
                return json.dumps({
                    "erro": True,
                    "mensagem": f"Desculpe, só fazemos entregas em {restaurante.cidade.title()}. O endereço informado parece ser fora da nossa área de entrega.",
                })

            config = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == restaurante_id
            ).first()
            taxa_entrega = config.taxa_entrega_base if config else 5.0

            bairro_cliente = args.get("bairro", "").strip()
            if not bairro_cliente and endereco_entrega:
                if cliente:
                    end_padrao = db.query(models.EnderecoCliente).filter(
                        models.EnderecoCliente.cliente_id == cliente.id,
                        models.EnderecoCliente.padrao == True,
                    ).first()
                    if end_padrao and end_padrao.bairro:
                        bairro_cliente = end_padrao.bairro

            if bairro_cliente:
                bairro_db = db.query(models.BairroEntrega).filter(
                    models.BairroEntrega.restaurante_id == restaurante_id,
                    models.BairroEntrega.ativo == True,
                    models.BairroEntrega.nome.ilike(f"%{bairro_cliente}%"),
                ).first()
                if bairro_db:
                    taxa_entrega = bairro_db.taxa_entrega
                else:
                    tem_bairros = db.query(models.BairroEntrega).filter(
                        models.BairroEntrega.restaurante_id == restaurante_id,
                        models.BairroEntrega.ativo == True,
                    ).count()
                    if tem_bairros > 0:
                        logger.info(f"Bairro '{bairro_cliente}' não cadastrado para restaurante {restaurante_id}, usando taxa padrão")

    valor_total_final = valor_total + taxa_entrega

    # Pix Online: SOMENTE quando forma_pagamento='pix_online' explicitamente
    # forma_pagamento='pix' = Pix na entrega (manual, como dinheiro)
    forma_pagamento = args.get("forma_pagamento", "dinheiro")
    pix_online = False
    pix_config = None
    if forma_pagamento == "pix_online":
        try:
            pix_config = db.query(models.PixConfig).filter(
                models.PixConfig.restaurante_id == restaurante_id,
                models.PixConfig.ativo == True,
            ).first()
            if pix_config:
                pix_online = True
            else:
                # Restaurante não tem Pix Online ativo — tratar como pix na entrega
                forma_pagamento = "pix"
        except Exception:
            forma_pagamento = "pix"

    # Criar pedido — STATUS:
    # - Se Pix Online: pendente (aguarda pagamento)
    # - Se impressão automática: em_preparo
    # - Senão: pendente
    if pix_online:
        status_inicial = "pendente"
    else:
        status_inicial = "em_preparo" if bot_config.impressao_automatica_bot else "pendente"

    pedido = models.Pedido(
        restaurante_id=restaurante_id,
        cliente_id=cliente.id if cliente else None,
        comanda=comanda,
        tipo="delivery" if tipo_entrega == "entrega" else "retirada",
        origem="whatsapp_bot",
        marketplace_source="derekh_whatsapp",
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
        forma_pagamento=forma_pagamento,
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

    # Montar link de rastreamento
    codigo_acesso = restaurante.codigo_acesso if restaurante else ""
    link_rastreamento = f"{BASE_URL}/cliente/{codigo_acesso}/order/{pedido.id}" if codigo_acesso else None

    # Info de entrega para confirmação (bairro/distância)
    bairro_entrega = ""
    distancia_km = 0
    if endereco_validado:
        bairro_entrega = endereco_validado.get("bairro", "")
        distancia_km = endereco_validado.get("distancia_km", 0)

    resultado = {
        "sucesso": True,
        "pedido_id": pedido.id,
        "comanda": comanda,
        "status": status_inicial,
        "itens": itens_texto,
        "valor_subtotal": valor_total,
        "taxa_entrega": taxa_entrega,
        "bairro_entrega": bairro_entrega,
        "distancia_km": distancia_km,
        "valor_total": valor_total_final,
        "link_rastreamento": link_rastreamento,
        "mensagem": f"Pedido #{comanda} criado! Valor: R${valor_total_final:.2f}. Status: {status_inicial}",
    }

    # Pix Online: gerar cobrança automaticamente
    if pix_online:
        try:
            from ..pix.pix_service import criar_cobranca_pedido
            pix_data = await criar_cobranca_pedido(pedido.id, db)
            resultado["pix_online"] = True
            resultado["pix_payment_link"] = pix_data.get("payment_link_url", "")
            resultado["pix_br_code"] = pix_data.get("br_code", "")
            resultado["mensagem"] = (
                f"Pedido #{comanda} criado! Valor: R${valor_total_final:.2f}. "
                f"Pagamento Pix pendente — envie o link ao cliente."
            )
            logger.info(f"Cobrança Pix gerada para pedido #{comanda} via WhatsApp Bot")
        except Exception as e:
            logger.error(f"Erro ao gerar cobrança Pix para pedido #{comanda}: {e}")
            # Fallback: mudar para Pix na entrega em vez de deixar pendente
            pedido.status = "em_preparo" if bot_config.impressao_automatica_bot else "pendente"
            pedido.forma_pagamento = "pix"
            # Criar PedidoCozinha se KDS ativo e status em_preparo
            if config_cozinha and config_cozinha.kds_ativo and pedido.status == "em_preparo":
                pedido_cozinha_fallback = models.PedidoCozinha(
                    restaurante_id=restaurante_id,
                    pedido_id=pedido.id,
                    status="NOVO",
                )
                db.add(pedido_cozinha_fallback)
            db.commit()
            resultado["pix_online"] = False
            resultado["pix_fallback"] = True
            resultado["status"] = pedido.status
            resultado["mensagem"] = (
                f"Pedido #{comanda} criado! Valor: R${valor_total_final:.2f}. "
                f"Não consegui gerar o link de pagamento, mas seu pedido foi criado! "
                f"Você pode pagar Pix na entrega."
            )

    return json.dumps(resultado)


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

    # Verificar se cozinha já começou a preparar (respeitar KDS)
    pedido_cozinha = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.pedido_id == pedido.id,
    ).first()
    if pedido_cozinha and pedido_cozinha.status not in ("NOVO",):
        return json.dumps({
            "erro": f"A cozinha já começou a preparar o pedido #{pedido.comanda}! Não consigo alterar agora 😅",
            "status_cozinha": pedido_cozinha.status,
        })

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
                models.Produto.restaurante_id == restaurante_id,
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

    resultado = {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "status_texto": status_map.get(pedido.status, pedido.status),
        "valor_total": pedido.valor_total,
        "itens": pedido.itens,
        "criado_em": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
    }

    # Tempo desde criação
    if pedido.data_criacao:
        minutos = int((datetime.utcnow() - pedido.data_criacao).total_seconds() / 60)
        resultado["minutos_desde_criacao"] = minutos

    # Histórico de status com timestamps
    if pedido.historico_status:
        resultado["historico_status"] = pedido.historico_status

    # Posição na fila da cozinha (se em_preparo)
    if pedido.status == "em_preparo":
        pedido_cozinha = db.query(models.PedidoCozinha).filter(
            models.PedidoCozinha.pedido_id == pedido.id,
        ).first()
        if pedido_cozinha:
            posicao = db.query(models.PedidoCozinha).filter(
                models.PedidoCozinha.restaurante_id == restaurante_id,
                models.PedidoCozinha.status.in_(["NOVO", "FAZENDO"]),
                models.PedidoCozinha.criado_em <= pedido_cozinha.criado_em,
                models.PedidoCozinha.pausado == False,
            ).count()
            resultado["posicao_fila"] = posicao
            resultado["status_cozinha"] = pedido_cozinha.status

    # Motoboy atribuído (se despachado/em_rota)
    if pedido.status in ("em_rota", "pronto"):
        entrega = db.query(models.Entrega).filter(
            models.Entrega.pedido_id == pedido.id,
        ).first()
        if entrega and entrega.motoboy_id:
            motoboy = db.query(models.Motoboy).filter(models.Motoboy.id == entrega.motoboy_id).first()
            if motoboy:
                resultado["motoboy_nome"] = motoboy.nome

    return json.dumps(resultado)


def _verificar_horario(db: Session, restaurante_id: int) -> str:
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    if not config:
        return json.dumps({"erro": "Configuração não encontrada"})

    # Timezone dinâmico por país
    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    pais = getattr(rest, 'pais', None) or "BR"
    TIMEZONE_MAP = {
        "BR": -3, "PT": 0, "AO": 1, "MZ": 2, "CV": -1,
        "US": -5, "ES": 1, "FR": 1, "IT": 1, "DE": 1, "GB": 0,
    }
    offset = TIMEZONE_MAP.get(pais, -3)
    agora = datetime.utcnow() + timedelta(hours=offset)
    hora_atual = agora.strftime("%H:%M")
    dia_semana_nomes = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    dia = dia_semana_nomes[agora.weekday()]

    # Verificar horarios_por_dia primeiro
    horarios_por_dia = None
    if config.horarios_por_dia:
        try:
            horarios_por_dia = json.loads(config.horarios_por_dia)
        except Exception:
            horarios_por_dia = None

    aberto = False
    horarios_semana = {}

    if horarios_por_dia:
        for dia_nome in dia_semana_nomes:
            dia_cfg = horarios_por_dia.get(dia_nome, {})
            dia_ativo = dia_cfg.get("ativo", False)
            dia_abertura = dia_cfg.get("abertura", "")
            dia_fechamento = dia_cfg.get("fechamento", "")
            if dia_ativo and dia_abertura and dia_fechamento:
                horarios_semana[dia_nome] = f"{dia_abertura} às {dia_fechamento}"
            else:
                horarios_semana[dia_nome] = "FECHADO"

            if dia_nome == dia and dia_ativo and dia_abertura and dia_fechamento:
                if dia_abertura <= dia_fechamento:
                    if dia_abertura <= hora_atual <= dia_fechamento:
                        aberto = True
                else:
                    if hora_atual >= dia_abertura or hora_atual <= dia_fechamento:
                        aberto = True
    else:
        dias_abertos = (config.dias_semana_abertos or "").split(",")
        abertura = config.horario_abertura or "18:00"
        fechamento = config.horario_fechamento or "23:00"
        for dia_nome in dia_semana_nomes:
            if dia_nome in dias_abertos:
                horarios_semana[dia_nome] = f"{abertura} às {fechamento}"
            else:
                horarios_semana[dia_nome] = "FECHADO"
        if dia in dias_abertos:
            if abertura <= fechamento:
                if abertura <= hora_atual <= fechamento:
                    aberto = True
            else:
                if hora_atual >= abertura or hora_atual <= fechamento:
                    aberto = True

    return json.dumps({
        "aberto": aberto,
        "hora_atual": hora_atual,
        "dia_semana": dia,
        "horario_hoje": horarios_semana.get(dia, "Não configurado"),
        "horarios_semana": horarios_semana,
    })


def _buscar_promocoes(db: Session, restaurante_id: int, conversa: Optional[models.BotConversa] = None) -> str:
    from datetime import datetime as dt
    agora = dt.utcnow()

    # Promoções globais ativas
    promos = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante_id,
        models.Promocao.ativo == True,
        models.Promocao.cliente_id == None,  # Apenas globais
        (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora),
    ).all()

    combos = db.query(models.Combo).filter(
        models.Combo.restaurante_id == restaurante_id,
        models.Combo.ativo == True,
    ).all()

    result = {"promocoes": [], "combos": [], "cupons_exclusivos": []}
    for p in promos:
        if p.uso_limitado and p.usos_realizados >= (p.limite_usos or 0):
            continue
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

    # Buscar cupons exclusivos do cliente (se identificado na conversa)
    if conversa and conversa.cliente_id:
        exclusivos = db.query(models.Promocao).filter(
            models.Promocao.restaurante_id == restaurante_id,
            models.Promocao.cliente_id == conversa.cliente_id,
            models.Promocao.ativo == True,
            (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora),
        ).all()
        for e in exclusivos:
            if e.uso_limitado and e.usos_realizados >= (e.limite_usos or 0):
                continue
            validade = e.data_fim.strftime("%d/%m") if e.data_fim else "sem prazo"
            result["cupons_exclusivos"].append({
                "cupom": e.codigo_cupom,
                "desconto": f"{e.valor_desconto:.0f}%",
                "validade": validade,
                "tipo": e.tipo_cupom,
            })

    return json.dumps(result)


def _registrar_avaliacao(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    # Verificar se já existe avaliação pendente para o pedido (criada pelo worker)
    avaliacao = None
    if args.get("pedido_id"):
        avaliacao = db.query(models.BotAvaliacao).filter(
            models.BotAvaliacao.pedido_id == args["pedido_id"],
            models.BotAvaliacao.restaurante_id == restaurante_id,
            models.BotAvaliacao.status == "pendente",
        ).first()

    if avaliacao:
        avaliacao.nota = args["nota"]
        avaliacao.categoria = args.get("categoria")
        avaliacao.detalhe = args.get("detalhe")
        avaliacao.status = "respondida"
        avaliacao.respondido_em = datetime.utcnow()
        avaliacao.conversa_id = conversa.id if conversa else None
    else:
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
    resultado = {"sucesso": True, "nota": nota}

    if nota >= 4:
        resultado["mensagem"] = "Obrigado pela avaliação! 😊"
        # Verificar se deve pedir Google Maps review
        bot_config = db.query(models.BotConfig).filter(
            models.BotConfig.restaurante_id == restaurante_id
        ).first()
        if bot_config and bot_config.avaliacao_pedir_google_review and bot_config.google_maps_url:
            avaliacao.avaliou_maps = True
            db.commit()
            resultado["google_maps_url"] = bot_config.google_maps_url
            resultado["mensagem"] = f"Obrigado pela nota {nota}! 😊 Se puder, deixa uma avaliação pra gente no Google Maps: {bot_config.google_maps_url}"
    else:
        resultado["mensagem"] = "Sentimos muito pela experiência. Já registrei o problema e o responsável vai entrar em contato."

    return json.dumps(resultado)


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
    db.flush()

    # Buscar política configurada para o tipo de problema
    bot_config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante_id
    ).first()

    resultado = {"sucesso": True, "problema_id": problema.id}
    mensagem_acao = ""

    if bot_config:
        tipo = args["tipo"]
        politica_map = {
            "atraso": bot_config.politica_atraso,
            "item_errado": bot_config.politica_pedido_errado,
            "item_faltando": bot_config.politica_item_faltando,
            "qualidade": bot_config.politica_qualidade,
        }
        politica = politica_map.get(tipo) or {}
        if isinstance(politica, str):
            import json as _json
            try:
                politica = _json.loads(politica)
            except Exception:
                politica = {}

        acao = politica.get("acao", "desculpar")
        desconto_pct = politica.get("desconto_pct", 0)
        mensagem_custom = politica.get("mensagem", "")

        if acao in ("desconto_proximo", "cupom_fixo") and desconto_pct > 0:
            # Gerar cupom de desconto automático
            codigo = f"DESC{''.join(random.choices(string.digits, k=4))}"
            promo = models.Promocao(
                restaurante_id=restaurante_id,
                nome=f"Desconto compensação #{problema.id}",
                tipo_desconto="percentual",
                valor_desconto=desconto_pct,
                codigo_cupom=codigo,
                ativo=True,
                uso_limitado=True,
                limite_usos=1,
                usos_realizados=0,
            )
            db.add(promo)
            problema.resolucao_tipo = "desconto_proximo"
            problema.cupom_gerado = codigo
            problema.desconto_pct = desconto_pct
            problema.resolvido_automaticamente = True
            problema.resolvido = True
            problema.resolvido_em = datetime.utcnow()
            mensagem_acao = f"Como pedido de desculpas, gerei um cupom de {desconto_pct:.0f}% de desconto para o próximo pedido: {codigo}"
            resultado["cupom"] = codigo
            resultado["desconto_pct"] = desconto_pct

        elif acao == "brinde_reenviar":
            problema.resolucao_tipo = "brinde"
            problema.resolvido_automaticamente = True
            problema.resolvido = True
            problema.resolvido_em = datetime.utcnow()
            mensagem_acao = "Vou notificar a equipe para reenviar o item correto. O item errado fica como brinde!"

        elif acao == "reembolso_parcial" and desconto_pct > 0:
            problema.resolucao_tipo = "reembolso"
            problema.desconto_pct = desconto_pct
            problema.resolvido_automaticamente = True
            problema.resolvido = True
            problema.resolvido_em = datetime.utcnow()
            mensagem_acao = f"Vou solicitar um reembolso parcial de {desconto_pct:.0f}% do valor do pedido. A equipe vai processar."

        if mensagem_custom:
            mensagem_acao = mensagem_custom + (f" {mensagem_acao}" if mensagem_acao else "")

    db.commit()

    resultado["mensagem"] = mensagem_acao or "Problema registrado. O responsável será notificado imediatamente."
    resultado["acao_aplicada"] = problema.resolucao_tipo or "desculpar"
    return json.dumps(resultado)


def _aplicar_cupom(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa] = None) -> str:
    from datetime import datetime as dt
    agora = dt.utcnow()

    cupom = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante_id,
        models.Promocao.codigo_cupom == args["codigo_cupom"].upper(),
        models.Promocao.ativo == True,
        (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora),
    ).first()

    if not cupom:
        return json.dumps({"valido": False, "mensagem": "Cupom inválido ou expirado"})

    # Verificar se cupom exclusivo pertence ao cliente da conversa
    if cupom.cliente_id:
        cliente_id_conversa = conversa.cliente_id if conversa else None
        if not cliente_id_conversa or cupom.cliente_id != cliente_id_conversa:
            return json.dumps({"valido": False, "mensagem": "Este cupom é exclusivo para outro cliente"})

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
        conversa.status = "aguardando_handoff"
        conversa.handoff_em = datetime.utcnow()
        conversa.handoff_motivo = args.get("motivo", "Solicitado pelo cliente")
        db.commit()

        # Notificar painel admin via WebSocket (som distinto)
        try:
            import asyncio
            from ..main import manager

            restaurante = db.query(models.Restaurante).filter(
                models.Restaurante.id == restaurante_id
            ).first()

            asyncio.get_event_loop().create_task(
                manager.broadcast({
                    "tipo": "bot_handoff_solicitado",
                    "dados": {
                        "conversa_id": conversa.id,
                        "telefone": conversa.telefone,
                        "nome_cliente": conversa.nome_cliente or "Cliente",
                        "motivo": conversa.handoff_motivo,
                        "telefone_restaurante": restaurante.telefone if restaurante else "",
                    },
                }, restaurante_id)
            )
        except Exception:
            pass  # WebSocket é best-effort

    return json.dumps({
        "sucesso": True,
        "mensagem": "O responsável pelo restaurante foi notificado. Enquanto ele não responder, continue atendendo normalmente. Se o responsável não aceitar, sugira que o cliente ligue para o restaurante.",
    })


# ==================== NOVAS FUNÇÕES (Comportamento Avançado da Bia) ====================


def _rastrear_pedido(db: Session, restaurante_id: int, args: dict) -> str:
    """Rastreamento completo: status, fila cozinha, motoboy GPS, ETA, link tracking."""
    pedido = None
    if args.get("pedido_id"):
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == args["pedido_id"],
            models.Pedido.restaurante_id == restaurante_id,
        ).first()
    elif args.get("telefone"):
        tel = "".join(c for c in args["telefone"] if c.isdigit())
        pedido = db.query(models.Pedido).filter(
            models.Pedido.restaurante_id == restaurante_id,
            models.Pedido.cliente_telefone.like(f"%{tel[-8:]}"),
            models.Pedido.status.notin_(["entregue", "cancelado", "finalizado"]),
        ).order_by(models.Pedido.data_criacao.desc()).first()

    if not pedido:
        return json.dumps({"erro": "Nenhum pedido ativo encontrado"})

    status_map = {
        "pendente": "Recebido, aguardando confirmação",
        "em_preparo": "Sendo preparado na cozinha 👨‍🍳",
        "pronto": "Pronto! Aguardando entregador 📦",
        "em_rota": "A caminho do seu endereço 🛵",
        "entregue": "Entregue ✅",
        "cancelado": "Cancelado ❌",
        "agendado": "Agendado 📅",
    }

    resultado = {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "status_texto": status_map.get(pedido.status, pedido.status),
        "itens": pedido.itens,
        "valor_total": pedido.valor_total,
    }

    # Timeline de status
    if pedido.historico_status:
        resultado["timeline"] = pedido.historico_status

    # Tempo desde criação
    if pedido.data_criacao:
        minutos = int((datetime.utcnow() - pedido.data_criacao).total_seconds() / 60)
        resultado["minutos_desde_criacao"] = minutos

    # Posição na fila da cozinha
    if pedido.status == "em_preparo":
        pedido_cozinha = db.query(models.PedidoCozinha).filter(
            models.PedidoCozinha.pedido_id == pedido.id,
        ).first()
        if pedido_cozinha:
            posicao = db.query(models.PedidoCozinha).filter(
                models.PedidoCozinha.restaurante_id == restaurante_id,
                models.PedidoCozinha.status.in_(["NOVO", "FAZENDO"]),
                models.PedidoCozinha.criado_em <= pedido_cozinha.criado_em,
                models.PedidoCozinha.pausado == False,
            ).count()
            resultado["posicao_fila"] = posicao
            resultado["status_cozinha"] = pedido_cozinha.status
            # ETA baseado na fila
            config = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == restaurante_id
            ).first()
            tempo_medio = config.tempo_medio_preparo if config else 30
            resultado["eta_preparo_min"] = max(5, int(tempo_medio * max(1, posicao)))

    # Motoboy + GPS (se em rota ou despachado)
    if pedido.status in ("em_rota", "pronto"):
        entrega = db.query(models.Entrega).filter(
            models.Entrega.pedido_id == pedido.id,
        ).first()
        if entrega and entrega.motoboy_id:
            motoboy = db.query(models.Motoboy).filter(models.Motoboy.id == entrega.motoboy_id).first()
            if motoboy:
                resultado["motoboy_nome"] = motoboy.nome
                if motoboy.latitude_atual and motoboy.longitude_atual:
                    resultado["motoboy_gps"] = {
                        "lat": motoboy.latitude_atual,
                        "lng": motoboy.longitude_atual,
                    }
                if entrega.tempo_entrega:
                    resultado["eta_entrega_min"] = entrega.tempo_entrega

    # Link de rastreamento
    restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if restaurante and restaurante.codigo_acesso:
        resultado["link_rastreamento"] = f"{BASE_URL}/cliente/{restaurante.codigo_acesso}/order/{pedido.id}"

    return json.dumps(resultado)


def _trocar_item_pedido(db: Session, restaurante_id: int, bot_config: models.BotConfig, args: dict) -> str:
    """Troca item do pedido por outro do cardápio, respeitando status da cozinha."""
    if not bot_config.pode_alterar_pedido:
        return json.dumps({"erro": "Bot não tem permissão para alterar pedidos"})

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == args["pedido_id"],
        models.Pedido.restaurante_id == restaurante_id,
    ).first()

    if not pedido:
        return json.dumps({"erro": "Pedido não encontrado"})

    if pedido.status not in ("pendente", "em_preparo"):
        return json.dumps({"erro": f"Pedido #{pedido.comanda} não pode ser alterado (status: {pedido.status})"})

    # Verificar KDS
    pedido_cozinha = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.pedido_id == pedido.id,
    ).first()
    if pedido_cozinha and pedido_cozinha.status not in ("NOVO",):
        return json.dumps({
            "erro": f"A cozinha já começou a preparar o pedido #{pedido.comanda}! Não dá pra trocar agora 😅",
        })

    # Buscar item a remover
    item_remover_nome = args.get("item_remover", "").lower()
    itens_pedido = db.query(models.ItemPedido).filter(
        models.ItemPedido.pedido_id == pedido.id,
    ).all()

    item_encontrado = None
    for item in itens_pedido:
        produto = db.query(models.Produto).filter(
            models.Produto.id == item.produto_id,
            models.Produto.restaurante_id == restaurante_id,
        ).first()
        if produto and item_remover_nome in produto.nome.lower():
            item_encontrado = item
            break

    if not item_encontrado:
        return json.dumps({"erro": f"Item '{args.get('item_remover', '')}' não encontrado no pedido"})

    # Buscar novo produto
    item_novo_nome = args.get("item_novo", "").lower()
    novo_produto = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante_id,
        models.Produto.disponivel == True,
        models.Produto.nome.ilike(f"%{item_novo_nome}%"),
    ).first()

    if not novo_produto:
        return json.dumps({"erro": f"Item '{args.get('item_novo', '')}' não encontrado no cardápio ou indisponível"})

    # Remover item antigo
    db.delete(item_encontrado)

    # Adicionar novo item
    preco_novo = novo_produto.preco_promocional if novo_produto.promocao and novo_produto.preco_promocional else novo_produto.preco
    qtd = args.get("quantidade", 1)
    novo_item = models.ItemPedido(
        pedido_id=pedido.id,
        produto_id=novo_produto.id,
        quantidade=qtd,
        preco_unitario=preco_novo,
    )
    db.add(novo_item)
    db.flush()

    # Recalcular total
    itens_atualizados = db.query(models.ItemPedido).filter(models.ItemPedido.pedido_id == pedido.id).all()
    valor_subtotal = sum(i.preco_unitario * i.quantidade for i in itens_atualizados)
    pedido.valor_subtotal = valor_subtotal
    pedido.valor_total = valor_subtotal + (pedido.valor_taxa_entrega or 0)

    # Atualizar texto de itens
    itens_texto = []
    for i in itens_atualizados:
        prod = db.query(models.Produto).filter(models.Produto.id == i.produto_id).first()
        nome = prod.nome if prod else "?"
        itens_texto.append(f"{i.quantidade}x {nome}")
    pedido.itens = ", ".join(itens_texto)

    db.commit()
    return json.dumps({
        "sucesso": True,
        "removido": args.get("item_remover", ""),
        "adicionado": f"{qtd}x {novo_produto.nome} (R${preco_novo:.2f})",
        "novo_total": pedido.valor_total,
        "mensagem": f"Troca feita! Tirei {args.get('item_remover', '')} e coloquei {qtd}x {novo_produto.nome}. Novo total: R${pedido.valor_total:.2f}",
    })


def _consultar_tempo_entrega(db: Session, restaurante_id: int, args: dict) -> str:
    """Consulta tempo estimado real com base na fila da cozinha e bairro."""
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    tempo_medio_preparo = config.tempo_medio_preparo if config else 30

    # Calcular tempo real baseado na fila da cozinha
    pedidos_na_fila = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.restaurante_id == restaurante_id,
        models.PedidoCozinha.status.in_(["NOVO", "FAZENDO"]),
        models.PedidoCozinha.pausado == False,
    ).count()

    # Tempo base de preparo (ajustado pela fila)
    tempo_preparo = tempo_medio_preparo
    if pedidos_na_fila > 3:
        tempo_preparo += (pedidos_na_fila - 3) * 5  # +5min para cada pedido além de 3

    resultado = {
        "tempo_preparo_min": tempo_preparo,
        "pedidos_na_fila": pedidos_na_fila,
    }

    # Se bairro informado, buscar tempo e taxa de entrega
    bairro_nome = args.get("bairro", "").strip()
    if bairro_nome:
        bairro = db.query(models.BairroEntrega).filter(
            models.BairroEntrega.restaurante_id == restaurante_id,
            models.BairroEntrega.ativo == True,
            models.BairroEntrega.nome.ilike(f"%{bairro_nome}%"),
        ).first()
        if bairro:
            resultado["bairro"] = bairro.nome
            resultado["taxa_entrega"] = bairro.taxa_entrega
            resultado["tempo_entrega_bairro_min"] = bairro.tempo_estimado_min
            resultado["total_estimado_min"] = tempo_preparo + bairro.tempo_estimado_min
        else:
            # Bairro não encontrado — usar estimativa padrão
            site_config = db.query(models.SiteConfig).filter(
                models.SiteConfig.restaurante_id == restaurante_id
            ).first()
            tempo_entrega_padrao = site_config.tempo_entrega_estimado if site_config else 30
            taxa_padrao = config.taxa_entrega_base if config else 5.0
            resultado["bairro"] = bairro_nome
            resultado["bairro_nao_cadastrado"] = True
            resultado["taxa_entrega"] = taxa_padrao
            resultado["tempo_entrega_bairro_min"] = tempo_entrega_padrao
            resultado["total_estimado_min"] = tempo_preparo + tempo_entrega_padrao
    else:
        # Sem bairro — dar estimativa geral
        site_config = db.query(models.SiteConfig).filter(
            models.SiteConfig.restaurante_id == restaurante_id
        ).first()
        tempo_entrega_padrao = site_config.tempo_entrega_estimado if site_config else 30
        resultado["tempo_entrega_medio_min"] = tempo_entrega_padrao
        resultado["total_estimado_min"] = tempo_preparo + tempo_entrega_padrao

    return json.dumps(resultado)


def _consultar_bairros(db: Session, restaurante_id: int, args: dict) -> str:
    """Lista bairros atendidos com taxas de entrega."""
    query = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.restaurante_id == restaurante_id,
        models.BairroEntrega.ativo == True,
    )

    nome_filtro = args.get("nome_bairro", "").strip()
    if nome_filtro:
        query = query.filter(models.BairroEntrega.nome.ilike(f"%{nome_filtro}%"))

    bairros = query.order_by(models.BairroEntrega.nome).all()

    if not bairros:
        if nome_filtro:
            return json.dumps({"encontrados": 0, "mensagem": f"Nenhum bairro encontrado com '{nome_filtro}'. Pode ser que não entregamos nessa região."})

        # Sem bairros cadastrados — restaurante usa taxa fixa
        config = db.query(models.ConfigRestaurante).filter(
            models.ConfigRestaurante.restaurante_id == restaurante_id
        ).first()
        taxa = config.taxa_entrega_base if config else 5.0
        return json.dumps({
            "encontrados": 0,
            "taxa_fixa": True,
            "taxa_entrega_padrao": taxa,
            "mensagem": f"Entregamos em toda a cidade! Taxa fixa de R${taxa:.2f}",
        })

    lista = [{
        "nome": b.nome,
        "taxa_entrega": b.taxa_entrega,
        "tempo_estimado_min": b.tempo_estimado_min,
    } for b in bairros]

    return json.dumps({
        "encontrados": len(lista),
        "bairros": lista,
    })


def _normalize_text(text: str) -> str:
    """Remove acentos e normaliza texto para comparação."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.category(c).startswith('M')).lower()


def _reverse_geocode_country(lat: float, lng: float) -> Optional[str]:
    """Reverse geocoding direto para detectar país (ISO 2 letras). Mais confiável que forward geocode."""
    import os
    import requests as req
    token = os.getenv("MAPBOX_TOKEN")
    if not token:
        return None
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
        params = {"access_token": token, "types": "country", "language": "pt"}
        resp = req.get(url, params=params, timeout=10)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        for f in features:
            if "country" in f.get("place_type", []):
                code = (f.get("properties", {}).get("short_code") or "").upper()
                if code:
                    return code
    except Exception:
        pass
    return None


def _validar_endereco(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    """Valida endereço via Mapbox geocoding, calcula distância e taxa de entrega."""
    from utils.mapbox_api import autocomplete_address
    from utils.haversine import haversine

    endereco_texto = args.get("endereco_texto", "").strip()
    if not endereco_texto:
        return json.dumps({"erro": "Informe o endereço com rua e número"})

    restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not restaurante:
        return json.dumps({"erro": "Restaurante não encontrado"})

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    raio_km = config.raio_entrega_km if config else 10.0
    taxa_base = config.taxa_entrega_base if config else 5.0
    distancia_base_km = config.distancia_base_km if config else 3.0
    taxa_km_extra = config.taxa_km_extra if config else 1.5

    rest_lat = restaurante.latitude
    rest_lng = restaurante.longitude
    proximity = (rest_lat, rest_lng) if rest_lat and rest_lng else None

    # Determinar país do restaurante — auto-detectar se necessário (ANTES de enriquecer query)
    pais = getattr(restaurante, 'pais', None) or "BR"
    if pais == "BR" and rest_lat and rest_lng:
        # Verificar se coordenadas são realmente do Brasil (lat -35 a 5, lng -75 a -35)
        if not (-35 <= rest_lat <= 6 and -75 <= rest_lng <= -34):
            # Coordenadas fora do Brasil — detectar país real via reverse geocoding direto
            detected = _reverse_geocode_country(rest_lat, rest_lng)
            if detected:
                pais = detected
                # Salvar para cache futuro
                try:
                    restaurante.pais = pais
                    db.commit()
                    logger.info(f"País auto-detectado para restaurante {restaurante_id}: {pais}")
                except Exception:
                    db.rollback()
            else:
                # Fallback: não filtrar por país
                pais = None

    # Enriquecer query com cidade do restaurante se não inclusos (normalizar acentos)
    query = endereco_texto
    cidade = (restaurante.cidade or "").strip()
    estado = (restaurante.estado or "").strip()
    endereco_norm = _normalize_text(endereco_texto)
    cidade_norm = _normalize_text(cidade) if cidade else ""
    if cidade_norm and cidade_norm not in endereco_norm:
        query = f"{endereco_texto}, {cidade}"
        # Só adicionar estado se for código alfabético (ex: SP, RJ) — NÃO códigos numéricos (ex: 02, 11)
        if estado and estado.isalpha() and len(estado) <= 4:
            query = f"{query}, {estado}"

    sugestoes_raw = autocomplete_address(query, proximity, country=pais)

    # Fallback: sem cidade (query livre)
    if not sugestoes_raw and query != endereco_texto:
        sugestoes_raw = autocomplete_address(endereco_texto, proximity, country=pais)

    if not sugestoes_raw:
        return json.dumps({
            "encontrado": False,
            "mensagem": "Não encontrei esse endereço. Pode informar a rua completa com número?",
        })

    # Processar sugestões (max 3 para o cliente)
    sugestoes = []
    for s in sugestoes_raw[:5]:
        lat, lng = s["coordinates"]
        distancia = 0.0
        dentro_zona = True

        if rest_lat and rest_lng:
            distancia = haversine((rest_lat, rest_lng), (lat, lng))
            dentro_zona = distancia <= raio_km

        # Calcular taxa por distância
        if distancia <= distancia_base_km:
            taxa = taxa_base
        else:
            taxa = round(taxa_base + (distancia - distancia_base_km) * taxa_km_extra, 2)

        sugestoes.append({
            "place_name": s["place_name"],
            "lat": lat,
            "lng": lng,
            "distancia_km": round(distancia, 2),
            "dentro_zona": dentro_zona,
            "taxa_entrega": taxa,
        })

    # Salvar sugestões no session_data da conversa
    if conversa:
        session_data = conversa.session_data or {}
        session_data["endereco_sugestoes"] = sugestoes
        session_data["endereco_complemento"] = args.get("complemento", "")
        session_data["endereco_referencia"] = args.get("referencia", "")
        conversa.session_data = session_data
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(conversa, "session_data")
        db.flush()

    # Filtrar apenas dentro da zona para apresentar ao cliente
    dentro = [s for s in sugestoes if s["dentro_zona"]]
    fora = [s for s in sugestoes if not s["dentro_zona"]]

    # Filtrar por cidade do restaurante — evitar mostrar endereços de outras cidades/estados
    # Usa normalização de acentos: "Garvão" matches "garvao" no place_name do Mapbox
    cidade_rest = (restaurante.cidade or "").strip()
    cidade_rest_norm = _normalize_text(cidade_rest) if cidade_rest else ""
    if cidade_rest_norm and dentro:
        na_cidade = [s for s in dentro if cidade_rest_norm in _normalize_text(s["place_name"])]
        if na_cidade:
            dentro = na_cidade  # Priorizar resultados na cidade correta
        elif pais and pais != "BR":
            # Para países não-BR (ex: Portugal), vilas/freguesias podem não aparecer no place_name
            # Se está dentro do raio de entrega, aceitar resultado (a distância já valida)
            pass
        else:
            # Todos resultados dentro do raio mas em cidades erradas — pedir mais detalhes
            return json.dumps({
                "encontrado": False,
                "mensagem": f"Não encontrei esse endereço em {cidade_rest.title()}. Pode me informar o endereço completo com bairro e cidade?",
            })

    if not dentro and fora:
        # Todos fora da zona — verificar se estão em cidades erradas
        if cidade_rest_norm:
            na_cidade_fora = [s for s in fora if cidade_rest_norm in _normalize_text(s["place_name"])]
            if not na_cidade_fora and pais == "BR":
                # Nenhum resultado na cidade do restaurante (só bloquear para BR)
                return json.dumps({
                    "encontrado": False,
                    "mensagem": f"Não encontrei esse endereço em {cidade_rest.title()}. Pode me informar o endereço completo com bairro e cidade?",
                })
        return json.dumps({
            "encontrado": True,
            "confianca": "fora_zona",
            "mensagem": f"O endereço encontrado está fora da nossa área de entrega (máximo {raio_km:.0f} km). Gostaria de retirar no restaurante?",
            "sugestoes_fora": [{"place_name": s["place_name"], "distancia_km": s["distancia_km"]} for s in fora[:3]],
        })

    # Montar resposta baseada na confiança
    if len(dentro) == 1 and dentro[0]["distancia_km"] < 5:
        # Alta confiança — 1 resultado próximo
        s = dentro[0]
        letras = ["A"]
        return json.dumps({
            "encontrado": True,
            "confianca": "alta",
            "endereco": s["place_name"],
            "distancia_km": s["distancia_km"],
            "taxa_entrega": s["taxa_entrega"],
            "opcoes_texto": [f"A) {s['place_name']} — R${s['taxa_entrega']:.2f}"],
            "mensagem": f"Encontrei: {s['place_name']}. Taxa de entrega: R${s['taxa_entrega']:.2f}. Confirma?",
        })
    else:
        # Média confiança — múltiplas opções
        letras = ["A", "B", "C"]
        opcoes = []
        for i, s in enumerate(dentro[:3]):
            opcoes.append(f"{letras[i]}) {s['place_name']} — R${s['taxa_entrega']:.2f}")

        return json.dumps({
            "encontrado": True,
            "confianca": "media",
            "opcoes_texto": opcoes,
            "mensagem": "Encontrei esses endereços. Qual é o seu?\n" + "\n".join(opcoes),
        })


def _confirmar_endereco_validado(db: Session, restaurante_id: int, args: dict, conversa: Optional[models.BotConversa]) -> str:
    """Confirma endereço escolhido pelo cliente e salva com coordenadas GPS."""
    telefone = args.get("telefone", "")
    tel_limpo = "".join(c for c in telefone if c.isdigit())
    opcao_index = args.get("opcao_index", 0)

    # Buscar cliente
    cliente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    if not cliente:
        return json.dumps({"erro": "Cliente não encontrado. Cadastre primeiro."})

    # Buscar sugestões salvas
    if not conversa or not conversa.session_data:
        return json.dumps({"erro": "Nenhuma validação de endereço pendente. Use validar_endereco primeiro."})

    session_data = conversa.session_data or {}
    sugestoes = session_data.get("endereco_sugestoes", [])

    if not sugestoes:
        return json.dumps({"erro": "Nenhuma sugestão de endereço encontrada. Use validar_endereco primeiro."})

    if opcao_index < 0 or opcao_index >= len(sugestoes):
        return json.dumps({"erro": f"Opção inválida. Escolha entre 0 e {len(sugestoes) - 1}."})

    escolha = sugestoes[opcao_index]
    place_name = escolha["place_name"]
    lat = escolha["lat"]
    lng = escolha["lng"]
    taxa_entrega = escolha["taxa_entrega"]

    # Extrair bairro do place_name (formato: "Rua X, 123, Bairro, Cidade - UF, CEP, Brasil")
    partes = [p.strip() for p in place_name.split(",")]
    bairro = partes[2] if len(partes) > 2 else ""

    complemento = args.get("complemento", "") or session_data.get("endereco_complemento", "")
    referencia = args.get("referencia", "") or session_data.get("endereco_referencia", "")

    # Buscar/atualizar endereço padrão do cliente
    endereco_existente = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.padrao == True,
    ).first()

    if endereco_existente:
        endereco_existente.endereco_completo = place_name
        endereco_existente.bairro = bairro
        endereco_existente.complemento = complemento
        endereco_existente.referencia = referencia
        endereco_existente.latitude = lat
        endereco_existente.longitude = lng
        endereco_existente.validado_mapbox = True
    else:
        novo_endereco = models.EnderecoCliente(
            cliente_id=cliente.id,
            endereco_completo=place_name,
            bairro=bairro,
            complemento=complemento,
            referencia=referencia,
            latitude=lat,
            longitude=lng,
            validado_mapbox=True,
            padrao=True,
        )
        db.add(novo_endereco)

    # Salvar endereço validado no session_data para _criar_pedido usar
    session_data["endereco_validado"] = {
        "place_name": place_name,
        "lat": lat,
        "lng": lng,
        "bairro": bairro,
        "taxa_entrega": taxa_entrega,
        "distancia_km": escolha["distancia_km"],
        "complemento": complemento,
        "referencia": referencia,
    }
    # Limpar sugestões pendentes
    session_data.pop("endereco_sugestoes", None)
    session_data.pop("endereco_complemento", None)
    session_data.pop("endereco_referencia", None)
    conversa.session_data = session_data
    conversa.endereco_confirmado = place_name

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(conversa, "session_data")

    db.commit()

    endereco_display = place_name
    if complemento:
        endereco_display += f", {complemento}"

    logger.info(f"Endereço validado GPS para cliente {cliente.id}: {place_name} ({lat},{lng})")

    return json.dumps({
        "sucesso": True,
        "endereco": endereco_display,
        "bairro": bairro,
        "taxa_entrega": taxa_entrega,
        "distancia_km": escolha["distancia_km"],
        "validado_gps": True,
        "mensagem": f"Endereço confirmado: {endereco_display}. Taxa de entrega: R${taxa_entrega:.2f}",
    })


def _atualizar_endereco_cliente(db: Session, restaurante_id: int, args: dict) -> str:
    """Atualiza ou cadastra endereço de entrega do cliente."""
    telefone = args.get("telefone", "")
    tel_limpo = "".join(c for c in telefone if c.isdigit())

    cliente = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante_id,
        models.Cliente.telefone.like(f"%{tel_limpo[-8:]}"),
    ).first()

    if not cliente:
        return json.dumps({"erro": "Cliente não encontrado. Cadastre primeiro."})

    endereco_completo = args.get("endereco_completo", "").strip()
    bairro = args.get("bairro", "").strip()
    complemento = args.get("complemento", "").strip()
    referencia = args.get("referencia", "").strip()

    if not endereco_completo:
        return json.dumps({"erro": "Endereço completo é obrigatório"})

    # Validar bairro na área de entrega (se bairros cadastrados)
    if bairro:
        tem_bairros = db.query(models.BairroEntrega).filter(
            models.BairroEntrega.restaurante_id == restaurante_id,
            models.BairroEntrega.ativo == True,
        ).count()
        if tem_bairros > 0:
            bairro_encontrado = db.query(models.BairroEntrega).filter(
                models.BairroEntrega.restaurante_id == restaurante_id,
                models.BairroEntrega.ativo == True,
                models.BairroEntrega.nome.ilike(f"%{bairro}%"),
            ).first()
            if not bairro_encontrado:
                return json.dumps({
                    "erro": f"Infelizmente não entregamos no bairro '{bairro}' 😔",
                    "sugestao": "Consulte os bairros atendidos com consultar_bairros",
                })

    # Buscar endereço padrão existente
    endereco_existente = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.padrao == True,
    ).first()

    if endereco_existente:
        endereco_existente.endereco_completo = endereco_completo
        endereco_existente.bairro = bairro
        endereco_existente.complemento = complemento
        endereco_existente.referencia = referencia
        msg = "Endereço atualizado"
    else:
        novo_endereco = models.EnderecoCliente(
            cliente_id=cliente.id,
            endereco_completo=endereco_completo,
            bairro=bairro,
            complemento=complemento,
            referencia=referencia,
            padrao=True,
        )
        db.add(novo_endereco)
        msg = "Endereço cadastrado"

    db.commit()
    return json.dumps({
        "sucesso": True,
        "endereco": endereco_completo,
        "bairro": bairro,
        "mensagem": f"{msg} com sucesso!",
    })


# ==================== PIX ONLINE — FUNCTION CALLS ====================

async def _gerar_cobranca_pix(db: Session, restaurante_id: int, args: dict) -> str:
    """Gera nova cobrança Pix para um pedido (caso a anterior tenha expirado)."""
    pedido_id = args.get("pedido_id")
    if not pedido_id:
        return json.dumps({"erro": "pedido_id é obrigatório"})

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == restaurante_id,
    ).first()

    if not pedido:
        return json.dumps({"erro": "Pedido não encontrado"})

    # Invalidar cobrança anterior se expirada
    cobranca_antiga = db.query(models.PixCobranca).filter(
        models.PixCobranca.pedido_id == pedido_id,
        models.PixCobranca.status == "ACTIVE",
    ).first()
    if cobranca_antiga:
        if cobranca_antiga.expira_em and cobranca_antiga.expira_em < datetime.utcnow():
            cobranca_antiga.status = "EXPIRED"
            db.commit()
        else:
            # Cobrança ainda ativa — retornar ela
            return json.dumps({
                "sucesso": True,
                "pix_payment_link": cobranca_antiga.payment_link_url or "",
                "pix_br_code": cobranca_antiga.br_code or "",
                "mensagem": "Cobrança Pix já existe e ainda está ativa.",
            })

    try:
        from ..pix.pix_service import criar_cobranca_pedido
        pix_data = await criar_cobranca_pedido(pedido_id, db)
        return json.dumps({
            "sucesso": True,
            "pix_payment_link": pix_data.get("payment_link_url", ""),
            "pix_br_code": pix_data.get("br_code", ""),
            "mensagem": "Nova cobrança Pix gerada! Envie o link ao cliente.",
        })
    except Exception as e:
        return json.dumps({"erro": f"Erro ao gerar cobrança Pix: {e}"})


def _consultar_pagamento_pix(db: Session, restaurante_id: int, args: dict) -> str:
    """Consulta status do pagamento Pix de um pedido."""
    pedido_id = args.get("pedido_id")
    if not pedido_id:
        return json.dumps({"erro": "pedido_id é obrigatório"})

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == restaurante_id,
    ).first()

    if not pedido:
        return json.dumps({"erro": "Pedido não encontrado"})

    cobranca = db.query(models.PixCobranca).filter(
        models.PixCobranca.pedido_id == pedido_id,
        models.PixCobranca.restaurante_id == restaurante_id,
    ).order_by(models.PixCobranca.criado_em.desc()).first()

    if not cobranca:
        return json.dumps({
            "pago": False,
            "status": "sem_cobranca",
            "mensagem": "Nenhuma cobrança Pix encontrada para este pedido.",
        })

    pago = cobranca.status == "COMPLETED"
    return json.dumps({
        "pago": pago,
        "status": cobranca.status,
        "pago_em": cobranca.pago_em.isoformat() if cobranca.pago_em else None,
        "mensagem": "Pagamento confirmado!" if pago else f"Status: {cobranca.status}. Pagamento ainda não confirmado.",
    })
