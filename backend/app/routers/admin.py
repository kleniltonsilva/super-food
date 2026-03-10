# backend/app/routers/admin.py

"""
Router Super Admin - Gerenciamento de restaurantes, planos, métricas
Sprint 5 da migração v4.0
Tarefas 131-138
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import re
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

        # Criar categorias padrão baseado no tipo
        try:
            from ..utils.menu_templates import TEMPLATES_RESTAURANTE
            template = TEMPLATES_RESTAURANTE.get(dados.tipo_restaurante, {})
            categorias = template.get("categorias_padrao", [])
            for cat in categorias:
                categoria = models.CategoriaMenu(
                    restaurante_id=restaurante.id,
                    nome=cat["nome"],
                    icone=cat.get("icone", ""),
                    ordem_exibicao=cat.get("ordem", 0),
                    ativo=True
                )
                db.add(categoria)
        except Exception:
            pass  # Se falhar categorias, não impede criação

    db.commit()
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
