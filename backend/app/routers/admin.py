# backend/app/routers/admin.py

"""
Router Super Admin - Gerenciamento de restaurantes, planos, métricas
Sprint 5 da migração v4.0
Tarefas 131-138
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, cast, Integer, Float, String
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import re, os, logging, requests as http_requests
import secrets
import hashlib

from .. import models, database, auth

router = APIRouter(prefix="/api/admin", tags=["Super Admin"])


# ========== Schemas ==========

class RestauranteListItem(BaseModel):
    id: int
    nome_fantasia: str
    email: str
    telefone: str
    plano: str
    valor_plano: float
    status: Optional[str] = None
    ativo: bool
    codigo_acesso: str
    criado_em: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None
    total_pedidos: int = 0
    total_motoboys: int = 0

    class Config:
        from_attributes = True


class RestauranteCreateRequest(BaseModel):
    nome_fantasia: str
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: str
    telefone: str
    endereco_completo: str
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    plano: str = "Básico"
    valor_plano: float = 199.00
    limite_motoboys: int = 3
    # Site config
    criar_site: bool = True
    tipo_restaurante: str = "geral"
    whatsapp: Optional[str] = None


class RestauranteUpdateRequest(BaseModel):
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco_completo: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    plano: Optional[str] = None
    valor_plano: Optional[float] = None
    limite_motoboys: Optional[int] = None
    data_vencimento: Optional[datetime] = None


class RestauranteStatusUpdate(BaseModel):
    status: str  # ativo, suspenso, cancelado


class RestauranteDetalhe(BaseModel):
    id: int
    nome: str
    nome_fantasia: str
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: str
    telefone: str
    endereco_completo: str
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plano: str
    valor_plano: float
    limite_motoboys: int
    codigo_acesso: str
    ativo: bool
    status: Optional[str] = None
    criado_em: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanoInfo(BaseModel):
    nome: str
    valor: float
    motoboys: int
    descricao: str
    total_assinantes: int = 0


class PlanoUpdateRequest(BaseModel):
    valor: Optional[float] = None
    motoboys: Optional[int] = None
    descricao: Optional[str] = None


class MetricasResponse(BaseModel):
    total_restaurantes: int
    restaurantes_ativos: int
    restaurantes_suspensos: int
    restaurantes_cancelados: int
    receita_mensal: float
    receita_anual_projetada: float
    ticket_medio: float
    total_pedidos_hoje: int
    total_pedidos_mes: int
    total_motoboys: int
    motoboys_online: int
    distribuicao_planos: dict


class InadimplenteItem(BaseModel):
    id: int
    nome_fantasia: str
    email: str
    telefone: str
    plano: str
    valor_plano: float
    status: Optional[str] = None
    data_vencimento: Optional[datetime] = None
    dias_vencido: int = 0


# ========== Planos padrão ==========

PLANOS_PADRAO = {
    "Básico": {
        "valor": 199.00,
        "motoboys": 3,
        "descricao": "Ideal para pequenos restaurantes - até 3 motoboys simultâneos"
    },
    "Essencial": {
        "valor": 269.00,
        "motoboys": 6,
        "descricao": "Bom equilíbrio - até 6 motoboys simultâneos"
    },
    "Avançado": {
        "valor": 360.00,
        "motoboys": 12,
        "descricao": "Para crescimento - até 12 motoboys simultâneos"
    },
    "Premium": {
        "valor": 599.00,
        "motoboys": 999,
        "descricao": "Top: motoboys ilimitados + suporte prioritário"
    }
}


# ========== Endpoints ==========

# --- 131: GET /admin/restaurantes ---

@router.get("/restaurantes", response_model=List[RestauranteListItem])
def listar_restaurantes(
    status_filtro: Optional[str] = Query(None, alias="status"),
    plano: Optional[str] = None,
    busca: Optional[str] = None,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Lista todos os restaurantes com filtros opcionais."""
    query = db.query(models.Restaurante)

    # Filtros
    if status_filtro:
        query = query.filter(models.Restaurante.status == status_filtro)
    if plano:
        query = query.filter(models.Restaurante.plano == plano)
    if busca:
        busca_like = f"%{busca}%"
        query = query.filter(
            (models.Restaurante.nome_fantasia.ilike(busca_like)) |
            (models.Restaurante.email.ilike(busca_like)) |
            (models.Restaurante.telefone.ilike(busca_like))
        )

    restaurantes = query.order_by(models.Restaurante.criado_em.desc()).all()

    resultado = []
    for r in restaurantes:
        # Contar pedidos e motoboys
        total_pedidos = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id
        ).scalar() or 0
        total_motoboys = db.query(func.count(models.Motoboy.id)).filter(
            models.Motoboy.restaurante_id == r.id,
            models.Motoboy.status == 'ativo'
        ).scalar() or 0

        resultado.append(RestauranteListItem(
            id=r.id,
            nome_fantasia=r.nome_fantasia,
            email=r.email,
            telefone=r.telefone,
            plano=r.plano,
            valor_plano=r.valor_plano,
            status=r.status,
            ativo=r.ativo,
            codigo_acesso=r.codigo_acesso,
            criado_em=r.criado_em,
            data_vencimento=r.data_vencimento,
            total_pedidos=total_pedidos,
            total_motoboys=total_motoboys,
        ))

    return resultado


# --- 132: POST /admin/restaurantes ---

@router.post("/restaurantes")
def criar_restaurante(
    dados: RestauranteCreateRequest,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Cria um novo restaurante."""
    # Validar email único
    email_limpo = dados.email.strip().lower()
    existe_email = db.query(models.Restaurante).filter(
        models.Restaurante.email == email_limpo
    ).first()
    if existe_email:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado")

    # Validar CNPJ único (se informado)
    cnpj_limpo = None
    if dados.cnpj and dados.cnpj.strip():
        cnpj_limpo = re.sub(r'\D', '', dados.cnpj.strip())
        if cnpj_limpo:
            if len(cnpj_limpo) != 14:
                raise HTTPException(status_code=400, detail="CNPJ deve ter 14 dígitos")
            existe_cnpj = db.query(models.Restaurante).filter(
                models.Restaurante.cnpj == cnpj_limpo
            ).first()
            if existe_cnpj:
                raise HTTPException(
                    status_code=400,
                    detail=f"CNPJ já cadastrado no restaurante '{existe_cnpj.nome_fantasia}'"
                )

    # Validar telefone
    telefone_limpo = re.sub(r'\D', '', dados.telefone.strip())
    if len(telefone_limpo) < 10:
        raise HTTPException(status_code=400, detail="Telefone inválido (mínimo 10 dígitos)")

    # Validar nome
    if len(dados.nome_fantasia.strip()) < 3:
        raise HTTPException(status_code=400, detail="Nome fantasia deve ter pelo menos 3 caracteres")

    # Gerar senha padrão (primeiros 6 dígitos do telefone)
    senha_padrao = telefone_limpo[:6] if len(telefone_limpo) >= 6 else "123456"

    # Criar restaurante
    restaurante = models.Restaurante(
        nome=dados.nome_fantasia.strip(),
        nome_fantasia=dados.nome_fantasia.strip(),
        razao_social=dados.razao_social.strip() if dados.razao_social and dados.razao_social.strip() else None,
        cnpj=cnpj_limpo or None,
        email=email_limpo,
        telefone=telefone_limpo,
        endereco_completo=dados.endereco_completo.strip(),
        cidade=dados.cidade.strip() if dados.cidade else None,
        estado=dados.estado.strip() if dados.estado else None,
        cep=dados.cep.strip() if dados.cep else None,
        plano=dados.plano,
        valor_plano=dados.valor_plano,
        limite_motoboys=dados.limite_motoboys,
        ativo=True,
        status='ativo',
        data_vencimento=datetime.utcnow() + timedelta(days=30)
    )
    restaurante.gerar_codigo_acesso()
    restaurante.set_senha(senha_padrao)

    db.add(restaurante)
    db.flush()

    # Criar ConfigRestaurante padrão
    config = models.ConfigRestaurante(restaurante_id=restaurante.id)
    db.add(config)

    # Criar SiteConfig se solicitado
    if dados.criar_site:
        site_config = models.SiteConfig(
            restaurante_id=restaurante.id,
            tipo_restaurante=dados.tipo_restaurante,
            whatsapp_numero=dados.whatsapp if dados.whatsapp else None,
        )
        db.add(site_config)

    db.commit()
    db.refresh(restaurante)

    # Criar categorias + produtos + combos padrão (seed autossuficiente)
    if dados.criar_site and dados.tipo_restaurante:
        try:
            from database.seed.seed_produtos_padrao import criar_produtos_padrao
            total = criar_produtos_padrao(db, restaurante.id, dados.tipo_restaurante)
            if total > 0:
                db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Seed produtos padrão falhou: {e}")
            db.rollback()
            db.refresh(restaurante)

    return {
        **RestauranteDetalhe.model_validate(restaurante).model_dump(),
        "senha_padrao": senha_padrao,
    }


# --- 133: PUT /admin/restaurantes/{id} ---

@router.put("/restaurantes/{restaurante_id}", response_model=RestauranteDetalhe)
def atualizar_restaurante(
    restaurante_id: int,
    dados: RestauranteUpdateRequest,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Atualiza dados de um restaurante."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Validar email único se mudou
    if "email" in campos and campos["email"]:
        email_limpo = campos["email"].strip().lower()
        existe = db.query(models.Restaurante).filter(
            models.Restaurante.email == email_limpo,
            models.Restaurante.id != restaurante_id
        ).first()
        if existe:
            raise HTTPException(status_code=400, detail="Email já cadastrado em outro restaurante")
        campos["email"] = email_limpo

    # Validar CNPJ único se mudou
    if "cnpj" in campos and campos["cnpj"]:
        cnpj_limpo = re.sub(r'\D', '', campos["cnpj"].strip())
        if cnpj_limpo:
            existe = db.query(models.Restaurante).filter(
                models.Restaurante.cnpj == cnpj_limpo,
                models.Restaurante.id != restaurante_id
            ).first()
            if existe:
                raise HTTPException(status_code=400, detail="CNPJ já cadastrado em outro restaurante")
            campos["cnpj"] = cnpj_limpo
        else:
            campos["cnpj"] = None

    for campo, valor in campos.items():
        setattr(restaurante, campo, valor)

    # Sincronizar nome com nome_fantasia
    if "nome_fantasia" in campos:
        restaurante.nome = campos["nome_fantasia"]

    db.commit()
    db.refresh(restaurante)

    return restaurante


# --- 134: PUT /admin/restaurantes/{id}/status ---

@router.put("/restaurantes/{restaurante_id}/status")
def atualizar_status_restaurante(
    restaurante_id: int,
    dados: RestauranteStatusUpdate,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Atualiza status do restaurante (ativo/suspenso/cancelado). Também renova assinatura se ativando."""
    if dados.status not in ('ativo', 'suspenso', 'cancelado'):
        raise HTTPException(status_code=400, detail="Status deve ser: ativo, suspenso ou cancelado")

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    restaurante.status = dados.status
    restaurante.ativo = (dados.status == 'ativo')

    # Se ativando e vencido, renovar por 30 dias
    if dados.status == 'ativo':
        if not restaurante.data_vencimento or restaurante.data_vencimento < datetime.utcnow():
            restaurante.data_vencimento = datetime.utcnow() + timedelta(days=30)

    db.commit()

    return {
        "mensagem": f"Status atualizado para '{dados.status}'",
        "restaurante_id": restaurante_id,
        "status": dados.status,
        "ativo": restaurante.ativo,
        "data_vencimento": restaurante.data_vencimento.isoformat() if restaurante.data_vencimento else None
    }


# --- 135: GET /admin/planos ---

@router.get("/planos", response_model=List[PlanoInfo])
def listar_planos(
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Lista planos disponíveis com contagem de assinantes."""
    resultado = []
    for nome, info in PLANOS_PADRAO.items():
        total = db.query(func.count(models.Restaurante.id)).filter(
            models.Restaurante.plano == nome,
            models.Restaurante.ativo == True
        ).scalar() or 0

        resultado.append(PlanoInfo(
            nome=nome,
            valor=info["valor"],
            motoboys=info["motoboys"],
            descricao=info["descricao"],
            total_assinantes=total,
        ))

    return resultado


# --- 136: PUT /admin/planos/{id} ---

@router.put("/planos/{nome_plano}")
def atualizar_plano(
    nome_plano: str,
    dados: PlanoUpdateRequest,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Atualiza valores de um plano. Afeta novos restaurantes e renovações."""
    if nome_plano not in PLANOS_PADRAO:
        raise HTTPException(status_code=404, detail=f"Plano '{nome_plano}' não encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Atualizar plano em memória
    for campo, valor in campos.items():
        PLANOS_PADRAO[nome_plano][campo] = valor

    # Atualizar restaurantes existentes com este plano (valor e limite)
    restaurantes_plano = db.query(models.Restaurante).filter(
        models.Restaurante.plano == nome_plano
    ).all()

    atualizados = 0
    for r in restaurantes_plano:
        if "valor" in campos:
            r.valor_plano = campos["valor"]
        if "motoboys" in campos:
            r.limite_motoboys = campos["motoboys"]
        atualizados += 1

    db.commit()

    return {
        "mensagem": f"Plano '{nome_plano}' atualizado",
        "plano": PLANOS_PADRAO[nome_plano],
        "restaurantes_atualizados": atualizados
    }


# --- 137: GET /admin/metricas ---

@router.get("/metricas", response_model=MetricasResponse)
def obter_metricas(
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Retorna métricas gerais do sistema."""
    agora = datetime.utcnow()
    inicio_hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Restaurantes
    total_restaurantes = db.query(func.count(models.Restaurante.id)).scalar() or 0
    restaurantes_ativos = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'ativo'
    ).scalar() or 0
    restaurantes_suspensos = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'suspenso'
    ).scalar() or 0
    restaurantes_cancelados = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'cancelado'
    ).scalar() or 0

    # Receita
    receita_mensal = db.query(func.sum(models.Restaurante.valor_plano)).filter(
        models.Restaurante.status == 'ativo'
    ).scalar() or 0.0

    ticket_medio = receita_mensal / restaurantes_ativos if restaurantes_ativos > 0 else 0.0

    # Pedidos
    total_pedidos_hoje = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.data_criacao >= inicio_hoje
    ).scalar() or 0
    total_pedidos_mes = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.data_criacao >= inicio_mes
    ).scalar() or 0

    # Motoboys
    total_motoboys = db.query(func.count(models.Motoboy.id)).filter(
        models.Motoboy.status == 'ativo'
    ).scalar() or 0
    motoboys_online = db.query(func.count(models.Motoboy.id)).filter(
        models.Motoboy.status == 'ativo',
        models.Motoboy.disponivel == True
    ).scalar() or 0

    # Distribuição de planos
    planos_query = db.query(
        models.Restaurante.plano,
        func.count(models.Restaurante.id)
    ).filter(
        models.Restaurante.ativo == True
    ).group_by(
        models.Restaurante.plano
    ).all()
    distribuicao_planos = {plano: count for plano, count in planos_query}

    return MetricasResponse(
        total_restaurantes=total_restaurantes,
        restaurantes_ativos=restaurantes_ativos,
        restaurantes_suspensos=restaurantes_suspensos,
        restaurantes_cancelados=restaurantes_cancelados,
        receita_mensal=receita_mensal,
        receita_anual_projetada=receita_mensal * 12,
        ticket_medio=ticket_medio,
        total_pedidos_hoje=total_pedidos_hoje,
        total_pedidos_mes=total_pedidos_mes,
        total_motoboys=total_motoboys,
        motoboys_online=motoboys_online,
        distribuicao_planos=distribuicao_planos,
    )


# --- 138: GET /admin/inadimplentes ---

@router.get("/inadimplentes", response_model=List[InadimplenteItem])
def listar_inadimplentes(
    dias_tolerancia: int = Query(0, ge=0, description="Dias de tolerância após vencimento"),
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Lista restaurantes com assinatura vencida (inadimplentes)."""
    data_corte = datetime.utcnow() - timedelta(days=dias_tolerancia)

    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.data_vencimento != None,
        models.Restaurante.data_vencimento < data_corte,
        models.Restaurante.status != 'cancelado'
    ).order_by(
        models.Restaurante.data_vencimento.asc()
    ).all()

    resultado = []
    agora = datetime.utcnow()
    for r in restaurantes:
        dias_vencido = (agora - r.data_vencimento).days if r.data_vencimento else 0
        resultado.append(InadimplenteItem(
            id=r.id,
            nome_fantasia=r.nome_fantasia,
            email=r.email,
            telefone=r.telefone,
            plano=r.plano,
            valor_plano=r.valor_plano,
            status=r.status,
            data_vencimento=r.data_vencimento,
            dias_vencido=dias_vencido,
        ))

    return resultado


# --- GET /admin/analytics ---

@router.get("/analytics")
def obter_analytics(
    periodo: str = Query("30d"),
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Retorna analytics detalhados do sistema: faturamento, pedidos, tendências, saúde dos restaurantes."""
    # Validar período
    periodos_validos = {"7d": 7, "30d": 30, "90d": 90}
    dias = periodos_validos.get(periodo, 30)

    # Calcular datas
    agora = datetime.utcnow()
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    # Início da semana (segunda-feira)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    # Início do mês atual
    inicio_mes = hoje.replace(day=1)
    # Início e fim do mês anterior
    fim_mes_anterior = inicio_mes - timedelta(days=1)
    inicio_mes_anterior = fim_mes_anterior.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fim_mes_anterior = fim_mes_anterior.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Data limite baseada no período
    data_limite = hoje - timedelta(days=dias)

    # ==================== FATURAMENTO ====================

    # Faturamento hoje (entregues)
    faturamento_hoje = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.status == "entregue",
        models.Pedido.data_criacao >= hoje
    ).scalar() or 0.0

    # Faturamento semana (entregues)
    faturamento_semana = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.status == "entregue",
        models.Pedido.data_criacao >= inicio_semana
    ).scalar() or 0.0

    # Faturamento mês (entregues)
    faturamento_mes = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.status == "entregue",
        models.Pedido.data_criacao >= inicio_mes
    ).scalar() or 0.0

    # Faturamento mês anterior (só entregues)
    faturamento_mes_anterior = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.status == "entregue",
        models.Pedido.data_criacao >= inicio_mes_anterior,
        models.Pedido.data_criacao <= fim_mes_anterior
    ).scalar() or 0.0

    # Faturamento mês anterior bruto (todos pedidos)
    faturamento_mes_anterior_bruto = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.data_criacao >= inicio_mes_anterior,
        models.Pedido.data_criacao <= fim_mes_anterior
    ).scalar() or 0.0

    # ==================== PEDIDOS ====================

    pedidos_hoje = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.data_criacao >= hoje
    ).scalar() or 0

    pedidos_semana = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.data_criacao >= inicio_semana
    ).scalar() or 0

    pedidos_mes = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.data_criacao >= inicio_mes
    ).scalar() or 0

    cancelamentos_hoje = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.status == "cancelado",
        models.Pedido.data_criacao >= hoje
    ).scalar() or 0

    cancelamentos_semana = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.status == "cancelado",
        models.Pedido.data_criacao >= inicio_semana
    ).scalar() or 0

    cancelamentos_mes = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.status == "cancelado",
        models.Pedido.data_criacao >= inicio_mes
    ).scalar() or 0

    taxa_cancelamento_mes = round((cancelamentos_mes / pedidos_mes * 100), 2) if pedidos_mes > 0 else 0.0

    ticket_medio_real = db.query(func.coalesce(func.avg(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.status == "entregue",
        models.Pedido.data_criacao >= inicio_mes
    ).scalar() or 0.0
    ticket_medio_real = round(float(ticket_medio_real), 2)

    # ==================== TOP 5 RESTAURANTES ====================

    top_restaurantes_query = db.query(
        models.Restaurante.id,
        models.Restaurante.nome_fantasia,
        func.coalesce(func.sum(
            case(
                (models.Pedido.status == "entregue", models.Pedido.valor_total),
                else_=0.0
            )
        ), 0.0).label("faturamento"),
        func.count(models.Pedido.id).label("total_pedidos"),
        func.coalesce(func.avg(
            case(
                (models.Pedido.status == "entregue", models.Pedido.valor_total),
                else_=None
            )
        ), 0.0).label("ticket_medio"),
        func.coalesce(func.sum(
            case(
                (models.Pedido.status == "cancelado", 1),
                else_=0
            )
        ), 0).label("cancelamentos")
    ).outerjoin(
        models.Pedido,
        and_(
            models.Pedido.restaurante_id == models.Restaurante.id,
            models.Pedido.data_criacao >= inicio_mes
        )
    ).filter(
        models.Restaurante.ativo == True
    ).group_by(
        models.Restaurante.id,
        models.Restaurante.nome_fantasia
    ).order_by(
        func.coalesce(func.sum(
            case(
                (models.Pedido.status == "entregue", models.Pedido.valor_total),
                else_=0.0
            )
        ), 0.0).desc()
    ).limit(5).all()

    top_restaurantes = []
    for row in top_restaurantes_query:
        top_restaurantes.append({
            "id": row.id,
            "nome": row.nome_fantasia,
            "faturamento": round(float(row.faturamento), 2),
            "total_pedidos": int(row.total_pedidos),
            "ticket_medio": round(float(row.ticket_medio), 2),
            "cancelamentos": int(row.cancelamentos)
        })

    # ==================== TENDÊNCIA DIA A DIA ====================

    tendencia_query = db.query(
        func.date(models.Pedido.data_criacao).label("dia"),
        func.coalesce(func.sum(
            case(
                (models.Pedido.status == "entregue", models.Pedido.valor_total),
                else_=0.0
            )
        ), 0.0).label("faturamento"),
        func.count(models.Pedido.id).label("pedidos")
    ).filter(
        models.Pedido.data_criacao >= data_limite
    ).group_by(
        func.date(models.Pedido.data_criacao)
    ).order_by(
        func.date(models.Pedido.data_criacao)
    ).all()

    tendencia_faturamento = []
    for row in tendencia_query:
        tendencia_faturamento.append({
            "data": str(row.dia)[:10],
            "faturamento": round(float(row.faturamento), 2),
            "pedidos": int(row.pedidos)
        })

    # ==================== SAÚDE POR RESTAURANTE ====================

    restaurantes_ativos = db.query(models.Restaurante).filter(
        models.Restaurante.ativo == True
    ).all()

    saude_restaurantes = []
    for r in restaurantes_ativos:
        # Pedidos do dia
        r_pedidos_dia = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.data_criacao >= hoje
        ).scalar() or 0

        # Pedidos da semana
        r_pedidos_semana = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.data_criacao >= inicio_semana
        ).scalar() or 0

        # Pedidos do mês
        r_pedidos_mes = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.data_criacao >= inicio_mes
        ).scalar() or 0

        # Faturamento do mês (entregues)
        r_faturamento_mes = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.status == "entregue",
            models.Pedido.data_criacao >= inicio_mes
        ).scalar() or 0.0

        # Cancelamentos do mês
        r_cancelamentos_mes = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.status == "cancelado",
            models.Pedido.data_criacao >= inicio_mes
        ).scalar() or 0

        # Taxa de cancelamento
        r_taxa_cancelamento = round((r_cancelamentos_mes / r_pedidos_mes * 100), 2) if r_pedidos_mes > 0 else 0.0

        # Ticket médio (entregues do mês)
        r_ticket_medio = db.query(func.coalesce(func.avg(models.Pedido.valor_total), 0.0)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.status == "entregue",
            models.Pedido.data_criacao >= inicio_mes
        ).scalar() or 0.0

        # Último pedido
        ultimo_pedido = db.query(func.max(models.Pedido.data_criacao)).filter(
            models.Pedido.restaurante_id == r.id
        ).scalar()

        saude_restaurantes.append({
            "id": r.id,
            "nome": r.nome_fantasia,
            "plano": r.plano,
            "pedidos_dia": r_pedidos_dia,
            "pedidos_semana": r_pedidos_semana,
            "pedidos_mes": r_pedidos_mes,
            "faturamento_mes": round(float(r_faturamento_mes), 2),
            "cancelamentos_mes": r_cancelamentos_mes,
            "taxa_cancelamento": r_taxa_cancelamento,
            "ticket_medio": round(float(r_ticket_medio), 2),
            "ultimo_pedido": ultimo_pedido.isoformat() if ultimo_pedido else None
        })

    # ==================== INSIGHTS ====================

    # Horário pico — tentar func.extract, fallback para func.strftime (SQLite)
    try:
        horario_pico_query = db.query(
            func.extract('hour', models.Pedido.data_criacao).label("hora"),
            func.count(models.Pedido.id).label("total")
        ).filter(
            models.Pedido.data_criacao >= data_limite
        ).group_by(
            func.extract('hour', models.Pedido.data_criacao)
        ).order_by(
            func.count(models.Pedido.id).desc()
        ).first()
        if horario_pico_query:
            horario_pico = {"hora": int(horario_pico_query.hora), "total_pedidos": int(horario_pico_query.total)}
        else:
            horario_pico = {"hora": 0, "total_pedidos": 0}
    except Exception:
        # Fallback SQLite
        try:
            horario_pico_query = db.query(
                cast(func.strftime('%H', models.Pedido.data_criacao), Integer).label("hora"),
                func.count(models.Pedido.id).label("total")
            ).filter(
                models.Pedido.data_criacao >= data_limite
            ).group_by(
                func.strftime('%H', models.Pedido.data_criacao)
            ).order_by(
                func.count(models.Pedido.id).desc()
            ).first()
            if horario_pico_query:
                horario_pico = {"hora": int(horario_pico_query.hora), "total_pedidos": int(horario_pico_query.total)}
            else:
                horario_pico = {"hora": 0, "total_pedidos": 0}
        except Exception:
            horario_pico = {"hora": 0, "total_pedidos": 0}

    # Formas de pagamento no período
    formas_pagamento_query = db.query(
        models.Pedido.forma_pagamento,
        func.count(models.Pedido.id).label("total")
    ).filter(
        models.Pedido.data_criacao >= data_limite,
        models.Pedido.forma_pagamento != None
    ).group_by(
        models.Pedido.forma_pagamento
    ).order_by(
        func.count(models.Pedido.id).desc()
    ).all()

    total_formas = sum(row.total for row in formas_pagamento_query) if formas_pagamento_query else 0
    formas_pagamento = []
    for row in formas_pagamento_query:
        formas_pagamento.append({
            "forma": row.forma_pagamento or "Não informado",
            "total": int(row.total),
            "percentual": round((row.total / total_formas * 100), 2) if total_formas > 0 else 0.0
        })

    # Tipos de entrega no período
    tipos_entrega_query = db.query(
        models.Pedido.tipo_entrega,
        func.count(models.Pedido.id).label("total")
    ).filter(
        models.Pedido.data_criacao >= data_limite,
        models.Pedido.tipo_entrega != None
    ).group_by(
        models.Pedido.tipo_entrega
    ).order_by(
        func.count(models.Pedido.id).desc()
    ).all()

    total_tipos = sum(row.total for row in tipos_entrega_query) if tipos_entrega_query else 0
    tipos_entrega = []
    for row in tipos_entrega_query:
        tipos_entrega.append({
            "tipo": row.tipo_entrega or "Não informado",
            "total": int(row.total),
            "percentual": round((row.total / total_tipos * 100), 2) if total_tipos > 0 else 0.0
        })

    # Clientes novos na semana
    clientes_novos_semana = db.query(func.count(models.Cliente.id)).filter(
        models.Cliente.data_cadastro >= inicio_semana
    ).scalar() or 0

    # Restaurantes inativos (ativos mas sem pedido nos últimos 7 dias)
    data_7_dias = hoje - timedelta(days=7)
    # Subquery: restaurantes com pedido nos últimos 7 dias
    subquery_ativos = db.query(models.Pedido.restaurante_id).filter(
        models.Pedido.data_criacao >= data_7_dias
    ).distinct().subquery()

    restaurantes_inativos_query = db.query(models.Restaurante).filter(
        models.Restaurante.ativo == True,
        ~models.Restaurante.id.in_(db.query(subquery_ativos))
    ).all()

    restaurantes_inativos = []
    for r in restaurantes_inativos_query:
        ultimo_p = db.query(func.max(models.Pedido.data_criacao)).filter(
            models.Pedido.restaurante_id == r.id
        ).scalar()
        restaurantes_inativos.append({
            "id": r.id,
            "nome": r.nome_fantasia,
            "ultimo_pedido": ultimo_p.isoformat() if ultimo_p else None
        })

    # Motoboys ociosos (ativos mas sem entrega finalizada nos últimos 7 dias)
    subquery_motoboys_com_entrega = db.query(models.Entrega.motoboy_id).filter(
        models.Entrega.entregue_em >= data_7_dias,
        models.Entrega.status == "entregue"
    ).distinct().subquery()

    motoboys_ociosos = db.query(func.count(models.Motoboy.id)).filter(
        models.Motoboy.status == "ativo",
        ~models.Motoboy.id.in_(db.query(subquery_motoboys_com_entrega))
    ).scalar() or 0

    # Crescimento MoM (Month over Month)
    if faturamento_mes_anterior > 0:
        crescimento_mom = round((float(faturamento_mes) / float(faturamento_mes_anterior) - 1) * 100, 2)
    else:
        crescimento_mom = 0.0 if float(faturamento_mes) == 0 else 100.0

    # ==================== RESPOSTA ====================

    return {
        # Faturamento
        "faturamento_hoje": round(float(faturamento_hoje), 2),
        "faturamento_semana": round(float(faturamento_semana), 2),
        "faturamento_mes": round(float(faturamento_mes), 2),
        "faturamento_mes_anterior": round(float(faturamento_mes_anterior), 2),
        "faturamento_mes_anterior_bruto": round(float(faturamento_mes_anterior_bruto), 2),
        # Pedidos
        "pedidos_hoje": pedidos_hoje,
        "pedidos_semana": pedidos_semana,
        "pedidos_mes": pedidos_mes,
        "cancelamentos_hoje": cancelamentos_hoje,
        "cancelamentos_semana": cancelamentos_semana,
        "cancelamentos_mes": cancelamentos_mes,
        "taxa_cancelamento_mes": taxa_cancelamento_mes,
        "ticket_medio_real": ticket_medio_real,
        # Top 5 restaurantes
        "top_restaurantes": top_restaurantes,
        # Tendência
        "tendencia_faturamento": tendencia_faturamento,
        # Saúde
        "saude_restaurantes": saude_restaurantes,
        # Insights
        "horario_pico": horario_pico,
        "formas_pagamento": formas_pagamento,
        "tipos_entrega": tipos_entrega,
        "clientes_novos_semana": clientes_novos_semana,
        "restaurantes_inativos": restaurantes_inativos,
        "motoboys_ociosos": motoboys_ociosos,
        "crescimento_mom": crescimento_mom
    }


# ========== Autocomplete Endereço ==========

@router.get("/autocomplete-endereco")
def admin_autocomplete_endereco(
    query: str = Query(..., min_length=3),
    current_admin=Depends(auth.get_current_admin),
):
    """Autocomplete de endereço via Mapbox (sem proximidade — super admin)."""
    from utils.mapbox_api import autocomplete_address

    sugestoes = autocomplete_address(query)
    return {"sugestoes": sugestoes}


# ========== Sentry — Consultar Erros ==========

logger = logging.getLogger("superfood")

SENTRY_API_BASE = "https://sentry.io/api/0"


def _sentry_headers():
    """Retorna headers de autenticação para a API do Sentry."""
    token = os.getenv("SENTRY_AUTH_TOKEN", "")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _sentry_org():
    return os.getenv("SENTRY_ORG", "derekh-food")


def _sentry_project(projeto: str):
    """Resolve slug do projeto Sentry."""
    mapping = {
        "api": os.getenv("SENTRY_PROJECT_API", "derekh-food-api"),
        "frontend": os.getenv("SENTRY_PROJECT_FRONTEND", "derekh-food-frontend"),
    }
    return mapping.get(projeto, projeto)


@router.get("/erros")
def listar_erros_sentry(
    projeto: str = Query("api", regex="^(api|frontend)$"),
    periodo: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    status_filtro: str = Query("todos", regex="^(todos|unresolved|resolved|ignored)$"),
    current_admin=Depends(auth.get_current_admin),
):
    """Lista issues do Sentry com filtros de projeto, período e status."""
    headers = _sentry_headers()
    if not headers:
        raise HTTPException(status_code=503, detail="SENTRY_AUTH_TOKEN não configurado")

    org = _sentry_org()
    project_slug = _sentry_project(projeto)

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    delta_map = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    delta = delta_map.get(periodo, timedelta(hours=24))

    # Query de status
    query_map = {
        "todos": "",
        "unresolved": "is:unresolved",
        "resolved": "is:resolved",
        "ignored": "is:ignored",
    }
    query = query_map.get(status_filtro, "")

    params = {
        "sort": "date",
        "limit": 50,
        "start": (now - delta).strftime("%Y-%m-%dT%H:%M:%S"),
        "end": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if query:
        params["query"] = query

    try:
        resp = http_requests.get(
            f"{SENTRY_API_BASE}/projects/{org}/{project_slug}/issues/",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        issues = resp.json()
    except http_requests.RequestException as e:
        logger.warning(f"Sentry API erro: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao consultar Sentry: {str(e)[:200]}")

    resultado = []
    for issue in issues:
        metadata = issue.get("metadata", {})
        resultado.append({
            "id": issue.get("id"),
            "titulo": issue.get("title", ""),
            "culprit": issue.get("culprit", ""),
            "tipo": metadata.get("type", issue.get("type", "")),
            "valor": metadata.get("value", ""),
            "arquivo": metadata.get("filename", ""),
            "funcao": metadata.get("function", ""),
            "contagem": issue.get("count", 0),
            "usuarios_afetados": issue.get("userCount", 0),
            "primeira_vez": issue.get("firstSeen"),
            "ultima_vez": issue.get("lastSeen"),
            "nivel": issue.get("level", "error"),
            "status": issue.get("status", "unresolved"),
            "link": issue.get("permalink", ""),
        })

    # Contadores por status (para as tabs)
    contadores = {"total": len(resultado), "unresolved": 0, "resolved": 0, "ignored": 0}
    for e in resultado:
        s = e["status"]
        if s in contadores:
            contadores[s] += 1

    return {
        "erros": resultado,
        "contadores": contadores,
        "projeto": projeto,
        "periodo": periodo,
        "status_filtro": status_filtro,
    }


@router.get("/erros/{issue_id}")
def detalhe_erro_sentry(
    issue_id: str,
    current_admin=Depends(auth.get_current_admin),
):
    """Retorna detalhes de um issue do Sentry com texto formatado para copiar no Claude."""
    headers = _sentry_headers()
    if not headers:
        raise HTTPException(status_code=503, detail="SENTRY_AUTH_TOKEN não configurado")

    org = _sentry_org()

    try:
        # Busca detalhes do issue
        issue_resp = http_requests.get(
            f"{SENTRY_API_BASE}/issues/{issue_id}/",
            headers=headers,
            timeout=10,
        )
        issue_resp.raise_for_status()
        issue = issue_resp.json()

        # Busca último evento do issue (com stack trace completo)
        event_resp = http_requests.get(
            f"{SENTRY_API_BASE}/issues/{issue_id}/events/latest/",
            headers=headers,
            timeout=10,
        )
        event_resp.raise_for_status()
        event = event_resp.json()
    except http_requests.RequestException as e:
        logger.warning(f"Sentry API erro: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao consultar Sentry: {str(e)[:200]}")

    # Extrai stack trace formatado
    stack_frames = []
    exceptions = event.get("entries", [])
    for entry in exceptions:
        if entry.get("type") == "exception":
            for exc_value in entry.get("data", {}).get("values", []):
                exc_type = exc_value.get("type", "Exception")
                exc_msg = exc_value.get("value", "")
                stack_frames.append(f"## {exc_type}: {exc_msg}\n")

                for frame in exc_value.get("stacktrace", {}).get("frames", []):
                    filename = frame.get("filename", "?")
                    lineno = frame.get("lineNo", "?")
                    func_name = frame.get("function", "?")
                    context_line = frame.get("context_line", "").strip()

                    stack_frames.append(f"  File \"{filename}\", line {lineno}, in {func_name}")
                    if context_line:
                        stack_frames.append(f"    {context_line}")

    stack_text = "\n".join(stack_frames) if stack_frames else "Stack trace não disponível"

    # Tags relevantes
    tags = {t["key"]: t["value"] for t in event.get("tags", [])}

    # Monta texto formatado para copiar no Claude Code
    texto_claude = f"""## Erro Sentry — {issue.get('title', 'Sem título')}

**Projeto:** {issue.get('project', {}).get('slug', '?')}
**Ambiente:** {tags.get('environment', '?')}
**Nível:** {issue.get('level', 'error')}
**Primeira vez:** {issue.get('firstSeen', '?')}
**Última vez:** {issue.get('lastSeen', '?')}
**Ocorrências:** {issue.get('count', 0)}
**Usuários afetados:** {issue.get('userCount', 0)}

### Tags
{chr(10).join(f'- {k}: {v}' for k, v in tags.items() if k in ('app_type', 'browser', 'os', 'url', 'restaurante_codigo', 'restaurante_nome', 'restaurante_id', 'environment', 'server_name'))}

### Stack Trace
```
{stack_text}
```

### Contexto do Evento
- **URL:** {event.get('request', {}).get('url', 'N/A')}
- **Método:** {event.get('request', {}).get('method', 'N/A')}
- **User-Agent:** {tags.get('browser', 'N/A')}

Por favor, analise este erro e sugira uma correção."""

    return {
        "issue": {
            "id": issue.get("id"),
            "titulo": issue.get("title"),
            "culprit": issue.get("culprit"),
            "nivel": issue.get("level"),
            "contagem": issue.get("count"),
            "usuarios_afetados": issue.get("userCount"),
            "primeira_vez": issue.get("firstSeen"),
            "ultima_vez": issue.get("lastSeen"),
            "link": issue.get("permalink"),
            "projeto": issue.get("project", {}).get("slug"),
        },
        "stack_trace": stack_text,
        "tags": tags,
        "texto_claude": texto_claude,
    }
