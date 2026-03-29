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
import socket
import httpx

from .. import models, database, auth
from ..feature_flags import get_all_features, get_tier, FEATURE_LABELS, TIER_TO_PLANO
from ..email_service import enviar_email_boas_vindas, BASE_URL

# DDDs brasileiros válidos (67 DDDs)
DDDS_VALIDOS = {
    11, 12, 13, 14, 15, 16, 17, 18, 19,  # SP
    21, 22, 24,                            # RJ
    27, 28,                                # ES
    31, 32, 33, 34, 35, 37, 38,           # MG
    41, 42, 43, 44, 45, 46,               # PR
    47, 48, 49,                            # SC
    51, 53, 54, 55,                        # RS
    61,                                    # DF
    62, 64,                                # GO
    63,                                    # TO
    65, 66,                                # MT
    67,                                    # MS
    68,                                    # AC
    69,                                    # RO
    71, 73, 74, 75, 77,                   # BA
    79,                                    # SE
    81, 82, 83, 84, 85, 86, 87, 88, 89,  # PE/AL/PB/RN/CE/PI
    91, 92, 93, 94, 95, 96, 97, 98, 99,  # PA/AM/AP/RR/MA
}


def _validar_cpf_cnpj(valor: str) -> bool:
    """Valida CPF (11 dígitos) ou CNPJ (14 dígitos) por dígitos verificadores."""
    digits = re.sub(r'\D', '', valor)
    if len(digits) == 11:
        if len(set(digits)) == 1:
            return False
        soma = sum(int(digits[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        d1 = 0 if resto < 2 else 11 - resto
        if int(digits[9]) != d1:
            return False
        soma = sum(int(digits[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        d2 = 0 if resto < 2 else 11 - resto
        return int(digits[10]) == d2
    if len(digits) == 14:
        if len(set(digits)) == 1:
            return False
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(digits[i]) * pesos1[i] for i in range(12))
        resto = soma % 11
        d1 = 0 if resto < 2 else 11 - resto
        if int(digits[12]) != d1:
            return False
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(digits[i]) * pesos2[i] for i in range(13))
        resto = soma % 11
        d2 = 0 if resto < 2 else 11 - resto
        return int(digits[13]) == d2
    return False

router = APIRouter(prefix="/api/admin", tags=["Super Admin"])


# ========== Schemas ==========

class RestauranteListItem(BaseModel):
    id: int
    nome_fantasia: str
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: str
    telefone: str
    endereco_completo: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    plano: str
    valor_plano: float
    status: Optional[str] = None
    ativo: bool
    codigo_acesso: str
    criado_em: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None
    total_pedidos: int = 0
    total_motoboys: int = 0
    billing_status: Optional[str] = None
    trial_fim: Optional[datetime] = None
    dias_vencido: Optional[int] = None

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
    # Billing
    iniciar_trial: bool = True
    # Email
    enviar_email: bool = True


class CnpjLookupResponse(BaseModel):
    cnpj: str
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone_1: Optional[str] = None
    telefone_2: Optional[str] = None
    email: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    data_inicio_atividade: Optional[str] = None


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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    billing_status: Optional[str] = None  # manual, trial, active, overdue, suspended, canceled
    plano_tier: Optional[int] = None  # 1=Básico, 2=Essencial, 3=Avançado, 4=Premium


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


class PlanoFeatureInfo(BaseModel):
    key: str
    label: str
    new: bool = False


class PlanoInfo(BaseModel):
    nome: str
    valor: float
    motoboys: int
    descricao: str
    total_assinantes: int = 0
    tier: int = 1
    features: list[PlanoFeatureInfo] = []


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

def _get_planos_db(db: Session) -> dict:
    """Lê planos do banco de dados. Fallback para valores padrão."""
    try:
        planos_db = db.query(models.Plano).filter(models.Plano.ativo == True).order_by(models.Plano.ordem).all()
        if planos_db:
            return {
                p.nome: {"valor": p.valor, "motoboys": p.limite_motoboys, "descricao": p.descricao}
                for p in planos_db
            }
    except Exception:
        pass
    return {
        "Básico": {"valor": 169.90, "motoboys": 2, "descricao": "Ideal para começar"},
        "Essencial": {"valor": 279.90, "motoboys": 5, "descricao": "Para restaurantes em crescimento"},
        "Avançado": {"valor": 329.90, "motoboys": 10, "descricao": "Para operações maiores"},
        "Premium": {"valor": 527.00, "motoboys": 999, "descricao": "Sem limites"},
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
    query = db.query(models.Restaurante).filter(
        ~models.Restaurante.email.like("%@superfood.test")
    )

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
            razao_social=r.razao_social,
            cnpj=r.cnpj,
            email=r.email,
            telefone=r.telefone,
            endereco_completo=r.endereco_completo,
            cidade=r.cidade,
            estado=r.estado,
            plano=r.plano,
            valor_plano=r.valor_plano,
            status=r.status,
            ativo=r.ativo,
            codigo_acesso=r.codigo_acesso,
            criado_em=r.criado_em,
            data_vencimento=r.data_vencimento,
            total_pedidos=total_pedidos,
            total_motoboys=total_motoboys,
            billing_status=r.billing_status,
            trial_fim=r.trial_fim,
            dias_vencido=r.dias_vencido,
        ))

    return resultado


# --- CNPJ Lookup via BrasilAPI ---

@router.get("/cnpj/{cnpj}", response_model=CnpjLookupResponse)
async def consultar_cnpj(
    cnpj: str,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
):
    """Consulta dados do CNPJ via BrasilAPI."""
    digits = re.sub(r'\D', '', cnpj)
    if len(digits) != 14:
        raise HTTPException(status_code=400, detail="CNPJ deve ter 14 dígitos")
    if not _validar_cpf_cnpj(digits):
        raise HTTPException(status_code=400, detail="CNPJ inválido — dígitos verificadores incorretos")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://brasilapi.com.br/api/cnpj/v2/{digits}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout ao consultar BrasilAPI")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar BrasilAPI: {str(e)}")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na Receita Federal")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="Limite de consultas atingido. Tente novamente em 1 minuto.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"BrasilAPI retornou status {resp.status_code}")

    data = resp.json()

    # Montar endereço completo
    logradouro = data.get("logradouro") or ""
    numero = data.get("numero") or ""
    complemento = data.get("complemento") or ""

    # Montar telefone: pegar ddd_telefone_1
    telefone_1 = ""
    ddd_tel = data.get("ddd_telefone_1") or ""
    if ddd_tel:
        # BrasilAPI retorna no formato "DDXXXXXXXX" ou "DD XXXXXXXX"
        tel_digits = re.sub(r'\D', '', ddd_tel)
        if len(tel_digits) >= 10:
            telefone_1 = tel_digits

    telefone_2 = ""
    ddd_tel2 = data.get("ddd_telefone_2") or ""
    if ddd_tel2:
        tel_digits2 = re.sub(r'\D', '', ddd_tel2)
        if len(tel_digits2) >= 10:
            telefone_2 = tel_digits2

    return CnpjLookupResponse(
        cnpj=digits,
        razao_social=data.get("razao_social"),
        nome_fantasia=data.get("nome_fantasia") or None,
        logradouro=logradouro or None,
        numero=numero or None,
        complemento=complemento or None,
        bairro=data.get("bairro") or None,
        municipio=data.get("municipio") or None,
        uf=data.get("uf") or None,
        cep=data.get("cep") or None,
        telefone_1=telefone_1 or None,
        telefone_2=telefone_2 or None,
        email=data.get("email") or None,
        situacao_cadastral=str(data.get("descricao_situacao_cadastral", "")) or None,
        data_inicio_atividade=data.get("data_inicio_atividade") or None,
    )


# --- 132: POST /admin/restaurantes ---

@router.post("/restaurantes")
async def criar_restaurante(
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
            if len(cnpj_limpo) not in (11, 14):
                raise HTTPException(status_code=400, detail="CPF deve ter 11 dígitos ou CNPJ 14 dígitos")
            if not _validar_cpf_cnpj(cnpj_limpo):
                raise HTTPException(status_code=400, detail="CPF/CNPJ inválido — dígitos verificadores incorretos")
            existe_cnpj = db.query(models.Restaurante).filter(
                models.Restaurante.cnpj == cnpj_limpo
            ).first()
            if existe_cnpj:
                raise HTTPException(
                    status_code=400,
                    detail=f"CNPJ já cadastrado no restaurante '{existe_cnpj.nome_fantasia}'"
                )

    # Validar telefone com DDD
    telefone_limpo = re.sub(r'\D', '', dados.telefone.strip())
    if len(telefone_limpo) < 10 or len(telefone_limpo) > 11:
        raise HTTPException(status_code=400, detail="Telefone inválido (10 ou 11 dígitos com DDD)")
    ddd = int(telefone_limpo[:2])
    if ddd not in DDDS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"DDD {ddd:02d} inválido")
    numero_sem_ddd = telefone_limpo[2:]
    if len(telefone_limpo) == 11 and numero_sem_ddd[0] != '9':
        raise HTTPException(status_code=400, detail="Celular (11 dígitos) deve começar com 9 após o DDD")
    if len(telefone_limpo) == 10 and numero_sem_ddd[0] not in '2345':
        raise HTTPException(status_code=400, detail="Telefone fixo (10 dígitos) deve começar com 2-5 após o DDD")

    # Validar nome
    if len(dados.nome_fantasia.strip()) < 3:
        raise HTTPException(status_code=400, detail="Nome fantasia deve ter pelo menos 3 caracteres")

    # Gerar senha padrão (primeiros 6 dígitos do telefone)
    senha_padrao = telefone_limpo[:6] if len(telefone_limpo) >= 6 else "123456"

    # Resolver valores do plano a partir do banco (fonte única de verdade)
    planos_db = _get_planos_db(db)
    plano_info = planos_db.get(dados.plano)
    if plano_info:
        valor_plano = plano_info["valor"]
        limite_motoboys = plano_info["motoboys"]
    else:
        valor_plano = dados.valor_plano
        limite_motoboys = dados.limite_motoboys

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
        valor_plano=valor_plano,
        limite_motoboys=limite_motoboys,
        plano_tier=get_tier(dados.plano),
        ativo=True,
        status='ativo',
        data_vencimento=datetime.utcnow() + timedelta(days=30)
    )
    restaurante.gerar_codigo_acesso()
    restaurante.set_senha(senha_padrao)

    # Geocodificar endereço + detectar cidade/estado/país
    if dados.endereco_completo and dados.endereco_completo.strip():
        try:
            from utils.mapbox_api import geocode_address
            from utils.calculos import detectar_cidade_endereco
            coords = geocode_address(dados.endereco_completo.strip())
            if coords:
                restaurante.latitude = coords[0]
                restaurante.longitude = coords[1]
            info = detectar_cidade_endereco(dados.endereco_completo.strip())
            if info:
                if info.get("cidade") and not restaurante.cidade:
                    restaurante.cidade = info["cidade"]
                if info.get("estado") and not restaurante.estado:
                    restaurante.estado = info["estado"]
                if info.get("pais_codigo"):
                    restaurante.pais = info["pais_codigo"]
        except Exception:
            pass  # Salva restaurante mesmo sem geocoding

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

    # Iniciar trial se solicitado
    trial_dias = 15
    if dados.iniciar_trial:
        try:
            from ..billing.billing_service import iniciar_trial
            await iniciar_trial(restaurante.id, db, admin_id=current_admin.id)
            db.refresh(restaurante)
            # Ler trial_dias da config
            config_billing = db.query(models.ConfigBilling).first()
            if config_billing:
                trial_dias = config_billing.trial_dias or 15
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erro ao iniciar trial: {e}")

    # Enviar email de boas-vindas
    email_enviado = False
    if dados.enviar_email and email_limpo:
        try:
            link_painel = f"{BASE_URL}/admin/login"
            link_onboarding = f"{BASE_URL}/admin/inicio"
            resultado_email = await enviar_email_boas_vindas(
                email_destino=email_limpo,
                nome_fantasia=dados.nome_fantasia.strip(),
                codigo_acesso=restaurante.codigo_acesso,
                senha_padrao=senha_padrao,
                link_painel=link_painel,
                link_onboarding=link_onboarding,
            )
            email_enviado = resultado_email.get("enviado", False)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erro ao enviar email boas-vindas: {e}")

    return {
        **RestauranteDetalhe.model_validate(restaurante).model_dump(),
        "senha_padrao": senha_padrao,
        "email_enviado": email_enviado,
        "trial_dias": trial_dias,
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

    # Validar CPF/CNPJ se mudou
    if "cnpj" in campos and campos["cnpj"]:
        cnpj_limpo = re.sub(r'\D', '', campos["cnpj"].strip())
        if cnpj_limpo:
            if len(cnpj_limpo) not in (11, 14):
                raise HTTPException(status_code=400, detail="CPF deve ter 11 dígitos ou CNPJ 14 dígitos")
            if not _validar_cpf_cnpj(cnpj_limpo):
                raise HTTPException(status_code=400, detail="CPF/CNPJ inválido — dígitos verificadores incorretos")
            existe = db.query(models.Restaurante).filter(
                models.Restaurante.cnpj == cnpj_limpo,
                models.Restaurante.id != restaurante_id
            ).first()
            if existe:
                raise HTTPException(status_code=400, detail="CPF/CNPJ já cadastrado em outro restaurante")
            campos["cnpj"] = cnpj_limpo
        else:
            campos["cnpj"] = None

    # Validar billing_status se mudou
    if "billing_status" in campos and campos["billing_status"]:
        validos = ("manual", "trial", "active", "overdue", "suspended", "canceled")
        if campos["billing_status"] not in validos:
            raise HTTPException(status_code=400, detail=f"billing_status deve ser um de: {', '.join(validos)}")

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

    status_anterior = restaurante.status
    restaurante.status = dados.status
    restaurante.ativo = (dados.status == 'ativo')

    # Se ativando e vencido, renovar por 30 dias
    if dados.status == 'ativo':
        if not restaurante.data_vencimento or restaurante.data_vencimento < datetime.utcnow():
            restaurante.data_vencimento = datetime.utcnow() + timedelta(days=30)

    # Gerenciar domínios personalizados conforme status
    dominios = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.restaurante_id == restaurante_id
    ).all()

    dominios_alterados = 0
    if dominios:
        if dados.status in ('suspenso', 'cancelado'):
            # Suspender/cancelar: desativar domínios + remover certificados SSL do Fly.io
            for d in dominios:
                if d.ativo:
                    d.ativo = False
                    d.ssl_ativo = False
                    dominios_alterados += 1
                    # Remover certificado do Fly.io para liberar recursos e impedir acesso
                    _fly_delete_certificate(d.dominio)

        elif dados.status == 'ativo' and status_anterior in ('suspenso', 'cancelado'):
            # Reativar: restaurar domínios + re-registrar certificados no Fly.io
            for d in dominios:
                if not d.ativo:
                    d.ativo = True
                    dominios_alterados += 1
                    # Re-registrar certificado no Fly.io
                    _fly_add_certificate(d.dominio)

    db.commit()

    msg = f"Status atualizado para '{dados.status}'"
    if dominios_alterados > 0:
        acao = "desativado(s)" if dados.status in ('suspenso', 'cancelado') else "reativado(s)"
        msg += f". {dominios_alterados} domínio(s) {acao}."

    return {
        "mensagem": msg,
        "restaurante_id": restaurante_id,
        "status": dados.status,
        "ativo": restaurante.ativo,
        "data_vencimento": restaurante.data_vencimento.isoformat() if restaurante.data_vencimento else None,
        "dominios_alterados": dominios_alterados,
    }


# --- 135: GET /admin/planos ---

@router.get("/planos", response_model=List[PlanoInfo])
def listar_planos(
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db)
):
    """Lista planos disponíveis com contagem de assinantes e features."""
    from ..feature_flags import get_tier, get_features_list_for_plano, get_new_features_for_plano, FEATURE_LABELS

    planos = _get_planos_db(db)
    resultado = []
    for nome, info in planos.items():
        total = db.query(func.count(models.Restaurante.id)).filter(
            models.Restaurante.plano == nome,
            models.Restaurante.ativo == True
        ).scalar() or 0

        tier = get_tier(nome)
        all_features = get_features_list_for_plano(nome)
        new_features = get_new_features_for_plano(nome)

        resultado.append(PlanoInfo(
            nome=nome,
            valor=info["valor"],
            motoboys=info["motoboys"],
            descricao=info["descricao"],
            total_assinantes=total,
            tier=tier,
            features=[
                PlanoFeatureInfo(key=f, label=FEATURE_LABELS.get(f, f), new=f in new_features)
                for f in all_features
            ],
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
    """Atualiza valores de um plano. Persiste no BD e afeta restaurantes existentes."""
    plano_db = db.query(models.Plano).filter(models.Plano.nome == nome_plano).first()
    if not plano_db:
        raise HTTPException(status_code=404, detail=f"Plano '{nome_plano}' não encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Atualizar plano no BD
    if "valor" in campos:
        plano_db.valor = campos["valor"]
    if "motoboys" in campos:
        plano_db.limite_motoboys = campos["motoboys"]
    if "descricao" in campos:
        plano_db.descricao = campos["descricao"]

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
    db.refresh(plano_db)

    return {
        "mensagem": f"Plano '{nome_plano}' atualizado",
        "plano": {"valor": plano_db.valor, "motoboys": plano_db.limite_motoboys, "descricao": plano_db.descricao},
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

    # Restaurantes (excluindo demos)
    _no_demo = ~models.Restaurante.email.like("%@superfood.test")
    total_restaurantes = db.query(func.count(models.Restaurante.id)).filter(_no_demo).scalar() or 0
    restaurantes_ativos = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'ativo', _no_demo
    ).scalar() or 0
    restaurantes_suspensos = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'suspenso', _no_demo
    ).scalar() or 0
    restaurantes_cancelados = db.query(func.count(models.Restaurante.id)).filter(
        models.Restaurante.status == 'cancelado', _no_demo
    ).scalar() or 0

    # Receita (excluindo demos)
    receita_mensal = db.query(func.sum(models.Restaurante.valor_plano)).filter(
        models.Restaurante.status == 'ativo', _no_demo
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
    projeto: str = Query("api", pattern="^(api|frontend)$"),
    periodo: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
    status_filtro: str = Query("todos", pattern="^(todos|unresolved|resolved|ignored)$"),
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


# ========== Domínios Personalizados + Fly.io Certificates API ==========

FLY_API_BASE = "https://api.machines.dev/v1"
FLY_APP_NAME = "superfood-api"


def _fly_headers():
    """Retorna headers de autenticação para a API do Fly.io."""
    token = os.getenv("FLY_API_TOKEN", "")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _fly_add_certificate(hostname: str) -> dict:
    """Registra certificado ACME no Fly.io para o hostname."""
    headers = _fly_headers()
    if not headers:
        return {"ok": False, "erro": "FLY_API_TOKEN não configurado"}
    try:
        resp = http_requests.post(
            f"{FLY_API_BASE}/apps/{FLY_APP_NAME}/certificates/acme",
            headers=headers,
            json={"hostname": hostname},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return {"ok": True, "data": resp.json()}
        return {"ok": False, "erro": f"Fly.io retornou {resp.status_code}: {resp.text[:200]}"}
    except http_requests.RequestException as e:
        return {"ok": False, "erro": str(e)[:200]}


def _fly_check_certificate(hostname: str) -> dict:
    """Verifica status do certificado no Fly.io."""
    headers = _fly_headers()
    if not headers:
        return {"ok": False, "erro": "FLY_API_TOKEN não configurado"}
    try:
        resp = http_requests.post(
            f"{FLY_API_BASE}/apps/{FLY_APP_NAME}/certificates/{hostname}/check",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            return {"ok": True, "data": resp.json()}
        return {"ok": False, "erro": f"Fly.io retornou {resp.status_code}: {resp.text[:200]}"}
    except http_requests.RequestException as e:
        return {"ok": False, "erro": str(e)[:200]}


def _fly_delete_certificate(hostname: str) -> dict:
    """Remove certificado do Fly.io."""
    headers = _fly_headers()
    if not headers:
        return {"ok": False, "erro": "FLY_API_TOKEN não configurado"}
    try:
        resp = http_requests.delete(
            f"{FLY_API_BASE}/apps/{FLY_APP_NAME}/certificates/{hostname}",
            headers=headers,
            timeout=15,
        )
        if resp.status_code in (200, 204):
            return {"ok": True}
        return {"ok": False, "erro": f"Fly.io retornou {resp.status_code}: {resp.text[:200]}"}
    except http_requests.RequestException as e:
        return {"ok": False, "erro": str(e)[:200]}


class DominioCreateRequest(BaseModel):
    dominio: str


@router.get("/restaurantes/{restaurante_id}/dominios")
def listar_dominios_restaurante(
    restaurante_id: int,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Lista domínios personalizados de um restaurante."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    dominios = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.restaurante_id == restaurante_id
    ).order_by(models.DominioPersonalizado.criado_em.desc()).all()

    return [
        {
            "id": d.id,
            "dominio": d.dominio,
            "tipo": d.tipo,
            "verificado": d.verificado,
            "dns_verificado_em": d.dns_verificado_em.isoformat() if d.dns_verificado_em else None,
            "ssl_ativo": d.ssl_ativo,
            "ativo": d.ativo,
            "criado_em": d.criado_em.isoformat() if d.criado_em else None,
        }
        for d in dominios
    ]


@router.post("/restaurantes/{restaurante_id}/dominios")
def criar_dominio_restaurante(
    restaurante_id: int,
    dados: DominioCreateRequest,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Adiciona domínio personalizado a um restaurante + registra certificado SSL no Fly.io."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    dominio_limpo = dados.dominio.strip().lower()

    if not dominio_limpo or "." not in dominio_limpo:
        raise HTTPException(status_code=400, detail="Domínio inválido")

    existente = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.dominio == dominio_limpo
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Domínio já cadastrado no sistema")

    # Registrar certificado ACME no Fly.io
    fly_result = _fly_add_certificate(dominio_limpo)
    fly_msg = None
    if not fly_result["ok"]:
        fly_msg = f"Aviso: certificado Fly.io não registrado ({fly_result['erro']}). Tente verificar DNS depois."
        logger.warning(f"Fly.io cert add falhou para {dominio_limpo}: {fly_result['erro']}")

    dominio = models.DominioPersonalizado(
        restaurante_id=restaurante_id,
        dominio=dominio_limpo,
        tipo="cname",
    )
    db.add(dominio)
    db.commit()
    db.refresh(dominio)

    return {
        "id": dominio.id,
        "dominio": dominio.dominio,
        "tipo": dominio.tipo,
        "verificado": dominio.verificado,
        "ssl_ativo": dominio.ssl_ativo,
        "ativo": dominio.ativo,
        "criado_em": dominio.criado_em.isoformat() if dominio.criado_em else None,
        "fly_certificado": "registrado" if fly_result["ok"] else "pendente",
        "fly_aviso": fly_msg,
        "instrucoes": {
            "tipo": "CNAME",
            "nome": dominio_limpo.split(".")[0],
            "valor": "superfood-api.fly.dev",
            "ttl": 3600,
            "mensagem": f"Adicione um registro CNAME no DNS do seu domínio apontando para superfood-api.fly.dev",
        },
    }


@router.post("/dominios/{dominio_id}/verificar")
def verificar_dns_dominio_admin(
    dominio_id: int,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Verifica DNS + status do certificado SSL no Fly.io."""
    dominio = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.id == dominio_id,
    ).first()

    if not dominio:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")

    # 1. Verificar DNS local via socket
    dns_ok = False
    try:
        result = socket.getaddrinfo(dominio.dominio, 443)
        if result:
            dns_ok = True
    except socket.gaierror:
        pass

    # 2. Verificar certificado no Fly.io
    fly_result = _fly_check_certificate(dominio.dominio)
    ssl_status = "pendente"
    if fly_result["ok"]:
        cert_data = fly_result.get("data", {})
        # Fly.io retorna status do certificado ACME
        acme = cert_data.get("acme", {})
        acme_configured = acme.get("configured", False)
        if acme_configured:
            ssl_status = "ativo"
        elif dns_ok:
            ssl_status = "emitindo"
    else:
        # Se não tem cert no Fly.io, tenta registrar agora
        add_result = _fly_add_certificate(dominio.dominio)
        if add_result["ok"]:
            ssl_status = "registrado"

    # 3. Atualizar banco
    if dns_ok:
        dominio.verificado = True
        dominio.dns_verificado_em = datetime.utcnow()
        dominio.ssl_ativo = ssl_status == "ativo"
        db.commit()
        msg = f"DNS configurado! SSL: {ssl_status}."
        if ssl_status == "ativo":
            msg = f"DNS + SSL ativos! Site disponível em https://{dominio.dominio}"
        elif ssl_status == "emitindo":
            msg = f"DNS OK! Certificado SSL sendo emitido pelo Let's Encrypt. Aguarde alguns minutos."
        return {"verificado": True, "ssl_status": ssl_status, "mensagem": msg}

    return {
        "verificado": False,
        "ssl_status": ssl_status,
        "mensagem": "DNS ainda não propagou. Configure o CNAME apontando para superfood-api.fly.dev e aguarde até 48h.",
    }


@router.delete("/dominios/{dominio_id}")
def remover_dominio_admin(
    dominio_id: int,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Remove domínio personalizado + certificado SSL do Fly.io."""
    dominio = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.id == dominio_id,
    ).first()

    if not dominio:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")

    nome = dominio.dominio

    # Remover certificado do Fly.io
    fly_result = _fly_delete_certificate(nome)
    if not fly_result["ok"]:
        logger.warning(f"Fly.io cert delete falhou para {nome}: {fly_result.get('erro', '?')}")

    db.delete(dominio)
    db.commit()
    return {"mensagem": f"Domínio {nome} removido com sucesso"}


# ========== Credenciais Plataforma (Integrações Marketplace) ==========

class CredencialPlataformaRequest(BaseModel):
    marketplace: str  # ifood, 99food, rappi, keeta
    client_id: str
    client_secret: str
    config_json: Optional[dict] = None


@router.get("/integracoes/plataformas")
def listar_credenciais_plataforma(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Listar todas as credenciais de plataforma configuradas."""
    creds = db.query(models.CredencialPlataforma).all()

    resultado = []
    for c in creds:
        # Contar restaurantes conectados neste marketplace
        connected = db.query(func.count(models.IntegracaoMarketplace.id)).filter(
            models.IntegracaoMarketplace.marketplace == c.marketplace,
            models.IntegracaoMarketplace.authorization_status == 'authorized',
        ).scalar() or 0

        resultado.append({
            "id": c.id,
            "marketplace": c.marketplace,
            "client_id": c.client_id,
            "has_secret": bool(c.client_secret),
            "ativo": c.ativo,
            "config_json": c.config_json,
            "restaurantes_conectados": connected,
            "criado_em": c.criado_em.isoformat() if c.criado_em else None,
            "atualizado_em": c.atualizado_em.isoformat() if c.atualizado_em else None,
        })

    return resultado


@router.post("/integracoes/plataformas")
def salvar_credencial_plataforma(
    payload: CredencialPlataformaRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Criar ou atualizar credencial de plataforma para um marketplace."""
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == payload.marketplace
    ).first()

    if cred:
        cred.client_id = payload.client_id
        cred.client_secret = payload.client_secret
        if payload.config_json is not None:
            cred.config_json = payload.config_json
        cred.atualizado_em = datetime.utcnow()
        msg = f"Credencial {payload.marketplace} atualizada"
    else:
        cred = models.CredencialPlataforma(
            marketplace=payload.marketplace,
            client_id=payload.client_id,
            client_secret=payload.client_secret,
            ativo=True,
            config_json=payload.config_json,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow(),
        )
        db.add(cred)
        msg = f"Credencial {payload.marketplace} criada"

    db.commit()
    db.refresh(cred)

    return {
        "id": cred.id,
        "marketplace": cred.marketplace,
        "client_id": cred.client_id,
        "ativo": cred.ativo,
        "mensagem": msg,
    }


@router.put("/integracoes/plataformas/{marketplace}")
def atualizar_credencial_plataforma(
    marketplace: str,
    payload: CredencialPlataformaRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualizar credencial de plataforma existente."""
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == marketplace
    ).first()
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credencial {marketplace} não encontrada")

    cred.client_id = payload.client_id
    cred.client_secret = payload.client_secret
    if payload.config_json is not None:
        cred.config_json = payload.config_json
    cred.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(cred)

    return {
        "id": cred.id,
        "marketplace": cred.marketplace,
        "client_id": cred.client_id,
        "ativo": cred.ativo,
        "mensagem": f"Credencial {marketplace} atualizada",
    }


@router.delete("/integracoes/plataformas/{marketplace}")
def deletar_credencial_plataforma(
    marketplace: str,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Remover credencial de plataforma. Restaurantes conectados serão desconectados."""
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == marketplace
    ).first()
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credencial {marketplace} não encontrada")

    # Desativar integrações de restaurantes neste marketplace
    db.query(models.IntegracaoMarketplace).filter(
        models.IntegracaoMarketplace.marketplace == marketplace,
    ).update({
        "ativo": False,
        "authorization_status": "revoked",
    })

    db.delete(cred)
    db.commit()

    return {"mensagem": f"Credencial {marketplace} removida e restaurantes desconectados"}


@router.put("/integracoes/plataformas/{marketplace}/toggle")
def toggle_credencial_plataforma(
    marketplace: str,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Ativar/desativar credencial de plataforma."""
    cred = db.query(models.CredencialPlataforma).filter(
        models.CredencialPlataforma.marketplace == marketplace
    ).first()
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credencial {marketplace} não encontrada")

    cred.ativo = not cred.ativo
    cred.atualizado_em = datetime.utcnow()

    # Se desativando, desativar todas as integrações de restaurantes
    if not cred.ativo:
        db.query(models.IntegracaoMarketplace).filter(
            models.IntegracaoMarketplace.marketplace == marketplace,
        ).update({"ativo": False})

    db.commit()

    return {
        "marketplace": cred.marketplace,
        "ativo": cred.ativo,
        "mensagem": f"{marketplace} {'ativado' if cred.ativo else 'desativado'}",
    }


@router.get("/integracoes/status")
def status_global_integracoes(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Status global de todas as integrações (restaurantes conectados, erros recentes)."""
    creds = db.query(models.CredencialPlataforma).all()

    resultado = []
    for c in creds:
        connected = db.query(func.count(models.IntegracaoMarketplace.id)).filter(
            models.IntegracaoMarketplace.marketplace == c.marketplace,
            models.IntegracaoMarketplace.authorization_status == 'authorized',
            models.IntegracaoMarketplace.ativo == True,
        ).scalar() or 0

        pending = db.query(func.count(models.IntegracaoMarketplace.id)).filter(
            models.IntegracaoMarketplace.marketplace == c.marketplace,
            models.IntegracaoMarketplace.authorization_status == 'pending',
        ).scalar() or 0

        # Erros recentes (últimas 24h)
        erros = db.query(func.count(models.MarketplaceEventLog.id)).filter(
            models.MarketplaceEventLog.marketplace == c.marketplace,
            models.MarketplaceEventLog.processed == False,
            models.MarketplaceEventLog.error_message.isnot(None),
            models.MarketplaceEventLog.criado_em >= datetime.utcnow() - timedelta(hours=24),
        ).scalar() or 0

        resultado.append({
            "marketplace": c.marketplace,
            "credencial_ativa": c.ativo,
            "restaurantes_conectados": connected,
            "restaurantes_pendentes": pending,
            "erros_24h": erros,
        })

    return resultado


# ========== Demos ==========

class DemoUpdateRequest(BaseModel):
    nome_fantasia: Optional[str] = None
    tema_cor_primaria: Optional[str] = None
    tema_cor_secundaria: Optional[str] = None


class DemoProdutoUpdateRequest(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    imagem_url: Optional[str] = None
    descricao: Optional[str] = None


class DemoSiteConfigUpdateRequest(BaseModel):
    logo_url: Optional[str] = None
    banner_principal_url: Optional[str] = None
    tema_cor_primaria: Optional[str] = None
    tema_cor_secundaria: Optional[str] = None
    tipo_restaurante: Optional[str] = None


@router.get("/demos")
def listar_demos(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Lista todos os restaurantes demo com estatísticas."""
    demos = db.query(models.Restaurante).filter(
        models.Restaurante.email.like("%@superfood.test")
    ).order_by(models.Restaurante.id).all()

    resultado = []
    for r in demos:
        site_config = db.query(models.SiteConfig).filter(
            models.SiteConfig.restaurante_id == r.id
        ).first()

        total_produtos = db.query(func.count(models.Produto.id)).filter(
            models.Produto.restaurante_id == r.id,
            models.Produto.disponivel == True,
        ).scalar() or 0

        total_categorias = db.query(func.count(models.CategoriaMenu.id)).filter(
            models.CategoriaMenu.restaurante_id == r.id,
            models.CategoriaMenu.ativo == True,
        ).scalar() or 0

        pedidos_recentes = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == r.id,
            models.Pedido.data_criacao >= datetime.utcnow() - timedelta(hours=24),
        ).scalar() or 0

        resultado.append({
            "id": r.id,
            "nome_fantasia": r.nome_fantasia,
            "codigo_acesso": r.codigo_acesso,
            "email": r.email,
            "ativo": r.ativo,
            "tipo_restaurante": site_config.tipo_restaurante if site_config else "geral",
            "logo_url": site_config.logo_url if site_config else None,
            "banner_principal_url": site_config.banner_principal_url if site_config else None,
            "tema_cor_primaria": site_config.tema_cor_primaria if site_config else "#E31A24",
            "tema_cor_secundaria": site_config.tema_cor_secundaria if site_config else "#1A1A2E",
            "total_produtos": total_produtos,
            "total_categorias": total_categorias,
            "pedidos_recentes_24h": pedidos_recentes,
        })

    return resultado


@router.get("/demos/{demo_id}")
def detalhe_demo(
    demo_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Detalhe completo de um restaurante demo: config, categorias, produtos."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == demo_id,
        models.Restaurante.email.like("%@superfood.test"),
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Demo não encontrado")

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()

    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()

    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante.id,
        models.CategoriaMenu.ativo == True,
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    categorias_result = []
    for cat in categorias:
        produtos = db.query(models.Produto).filter(
            models.Produto.restaurante_id == restaurante.id,
            models.Produto.categoria_id == cat.id,
            models.Produto.disponivel == True,
        ).order_by(models.Produto.ordem_exibicao, models.Produto.nome).all()

        categorias_result.append({
            "id": cat.id,
            "nome": cat.nome,
            "ordem_exibicao": cat.ordem_exibicao,
            "produtos": [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "descricao": p.descricao,
                    "preco": p.preco,
                    "imagem_url": p.imagem_url,
                    "destaque": p.destaque,
                    "promocao": p.promocao,
                    "preco_promocional": p.preco_promocional,
                }
                for p in produtos
            ],
        })

    return {
        "id": restaurante.id,
        "nome_fantasia": restaurante.nome_fantasia,
        "codigo_acesso": restaurante.codigo_acesso,
        "email": restaurante.email,
        "ativo": restaurante.ativo,
        "site_config": {
            "tipo_restaurante": site_config.tipo_restaurante if site_config else "geral",
            "logo_url": site_config.logo_url if site_config else None,
            "banner_principal_url": site_config.banner_principal_url if site_config else None,
            "tema_cor_primaria": site_config.tema_cor_primaria if site_config else "#E31A24",
            "tema_cor_secundaria": site_config.tema_cor_secundaria if site_config else "#1A1A2E",
            "pedido_minimo": site_config.pedido_minimo if site_config else 0,
            "tempo_entrega_estimado": site_config.tempo_entrega_estimado if site_config else 50,
        } if site_config else None,
        "config": {
            "raio_entrega_km": config_rest.raio_entrega_km if config_rest else 10,
            "taxa_entrega_base": config_rest.taxa_entrega_base if config_rest else 5,
        } if config_rest else None,
        "categorias": categorias_result,
    }


@router.put("/demos/{demo_id}")
def atualizar_demo(
    demo_id: int,
    dados: DemoUpdateRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza nome/cores de um restaurante demo."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == demo_id,
        models.Restaurante.email.like("%@superfood.test"),
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Demo não encontrado")

    if dados.nome_fantasia:
        restaurante.nome_fantasia = dados.nome_fantasia

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()
    if site_config:
        if dados.tema_cor_primaria:
            site_config.tema_cor_primaria = dados.tema_cor_primaria
        if dados.tema_cor_secundaria:
            site_config.tema_cor_secundaria = dados.tema_cor_secundaria

    db.commit()
    return {"mensagem": "Demo atualizado", "id": restaurante.id}


@router.put("/demos/{demo_id}/produto/{produto_id}")
def atualizar_produto_demo(
    demo_id: int,
    produto_id: int,
    dados: DemoProdutoUpdateRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza foto/nome/preço de um produto de demo."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == demo_id,
        models.Restaurante.email.like("%@superfood.test"),
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Demo não encontrado")

    produto = db.query(models.Produto).filter(
        models.Produto.id == produto_id,
        models.Produto.restaurante_id == restaurante.id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if dados.nome is not None:
        produto.nome = dados.nome
    if dados.preco is not None:
        produto.preco = dados.preco
    if dados.imagem_url is not None:
        produto.imagem_url = dados.imagem_url
    if dados.descricao is not None:
        produto.descricao = dados.descricao

    db.commit()
    return {"mensagem": "Produto atualizado", "produto_id": produto.id}


@router.put("/demos/{demo_id}/site-config")
def atualizar_site_config_demo(
    demo_id: int,
    dados: DemoSiteConfigUpdateRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza logo, banner, cores e tipo de um restaurante demo."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == demo_id,
        models.Restaurante.email.like("%@superfood.test"),
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Demo não encontrado")

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()
    if not site_config:
        raise HTTPException(status_code=404, detail="SiteConfig não encontrado")

    if dados.logo_url is not None:
        site_config.logo_url = dados.logo_url
    if dados.banner_principal_url is not None:
        site_config.banner_principal_url = dados.banner_principal_url
    if dados.tema_cor_primaria is not None:
        site_config.tema_cor_primaria = dados.tema_cor_primaria
    if dados.tema_cor_secundaria is not None:
        site_config.tema_cor_secundaria = dados.tema_cor_secundaria
    if dados.tipo_restaurante is not None:
        site_config.tipo_restaurante = dados.tipo_restaurante

    db.commit()
    return {"mensagem": "Site config atualizado"}


@router.post("/demos/{demo_id}/reset")
def reset_demo(
    demo_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Limpa pedidos e clientes do demo (mantém cardápio e config)."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == demo_id,
        models.Restaurante.email.like("%@superfood.test"),
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Demo não encontrado")

    # Deleta entregas dos pedidos
    pedido_ids = [p.id for p in db.query(models.Pedido.id).filter(
        models.Pedido.restaurante_id == restaurante.id
    ).all()]
    if pedido_ids:
        db.query(models.Entrega).filter(
            models.Entrega.pedido_id.in_(pedido_ids)
        ).delete(synchronize_session=False)

    # Deleta pedidos
    deleted_pedidos = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == restaurante.id
    ).delete(synchronize_session=False)

    # Deleta clientes do demo
    deleted_clientes = db.query(models.Cliente).filter(
        models.Cliente.restaurante_id == restaurante.id
    ).delete(synchronize_session=False)

    # Deleta carrinhos
    db.query(models.Carrinho).filter(
        models.Carrinho.restaurante_id == restaurante.id
    ).delete(synchronize_session=False)

    db.commit()
    return {
        "mensagem": "Demo resetado",
        "pedidos_removidos": deleted_pedidos,
        "clientes_removidos": deleted_clientes,
    }


# ============================================================
# FEATURE FLAGS — Override por restaurante
# ============================================================

@router.get("/restaurantes/{restaurante_id}/features")
def get_features_restaurante(
    restaurante_id: int,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Retorna features atuais do restaurante (plan-based + overrides)."""
    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not rest:
        raise HTTPException(404, "Restaurante não encontrado")

    tier = getattr(rest, "plano_tier", None) or get_tier(rest.plano)
    overrides = getattr(rest, "features_override", None)
    features = get_all_features(rest.plano, overrides=overrides, plano_tier=tier)

    override_dict = {}
    if overrides:
        try:
            import json
            override_dict = json.loads(overrides) if isinstance(overrides, str) else overrides
        except Exception:
            pass

    return {
        "restaurante_id": rest.id,
        "plano": rest.plano,
        "plano_tier": tier,
        "billing_status": rest.billing_status,
        "features": features,
        "overrides": override_dict,
        "feature_labels": FEATURE_LABELS,
        "tier_planos": TIER_TO_PLANO,
    }


class FeatureOverrideRequest(BaseModel):
    overrides: dict  # {"kds_cozinha": true, "bridge_printer": false}


@router.put("/restaurantes/{restaurante_id}/features")
def set_features_override(
    restaurante_id: int,
    dados: FeatureOverrideRequest,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Define overrides de features para um restaurante. Super Admin pode dar/tirar features."""
    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not rest:
        raise HTTPException(404, "Restaurante não encontrado")

    import json
    # Merge com overrides existentes
    existing = {}
    if rest.features_override:
        try:
            existing = json.loads(rest.features_override) if isinstance(rest.features_override, str) else rest.features_override
        except Exception:
            existing = {}

    for key, val in dados.overrides.items():
        if val is None:
            existing.pop(key, None)  # None remove o override
        else:
            existing[key] = bool(val)

    rest.features_override = json.dumps(existing) if existing else None
    db.commit()

    tier = getattr(rest, "plano_tier", None) or get_tier(rest.plano)
    features = get_all_features(rest.plano, overrides=rest.features_override, plano_tier=tier)

    return {
        "restaurante_id": rest.id,
        "overrides": existing,
        "features": features,
    }


# ==================== Solicitações de Cadastro (Onboarding) ====================

class SolicitacaoStatusUpdate(BaseModel):
    status: str  # aprovado, rejeitado
    motivo: Optional[str] = None


class CriarRestauranteDeSolicitacao(BaseModel):
    endereco_completo: str = ""
    plano: str = "Básico"
    valor_plano: float = 169.90
    limite_motoboys: int = 2
    criar_site: bool = True
    tipo_restaurante: str = "geral"
    enviar_email: bool = True
    iniciar_trial: bool = True


@router.get("/solicitacoes")
def listar_solicitacoes(
    status: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Lista solicitações de cadastro (filtro por status e busca)."""
    query = db.query(models.SolicitacaoCadastro)

    if status:
        query = query.filter(models.SolicitacaoCadastro.status == status)
    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                models.SolicitacaoCadastro.nome_fantasia.ilike(termo),
                models.SolicitacaoCadastro.email.ilike(termo),
                models.SolicitacaoCadastro.telefone.ilike(termo),
                models.SolicitacaoCadastro.nome_responsavel.ilike(termo),
            )
        )

    solicitacoes = query.order_by(models.SolicitacaoCadastro.criado_em.desc()).all()

    # Contagem por status
    total_pendentes = db.query(func.count(models.SolicitacaoCadastro.id)).filter(
        models.SolicitacaoCadastro.status == "pendente"
    ).scalar() or 0

    return {
        "solicitacoes": [
            {
                "id": s.id,
                "nome_fantasia": s.nome_fantasia,
                "nome_responsavel": s.nome_responsavel,
                "email": s.email,
                "telefone": s.telefone,
                "cnpj": s.cnpj,
                "cidade": s.cidade,
                "estado": s.estado,
                "tipo_restaurante": s.tipo_restaurante,
                "mensagem": s.mensagem,
                "status": s.status,
                "motivo_rejeicao": s.motivo_rejeicao,
                "restaurante_id": s.restaurante_id,
                "criado_em": s.criado_em.isoformat() if s.criado_em else None,
                "atualizado_em": s.atualizado_em.isoformat() if s.atualizado_em else None,
                "ip_origem": s.ip_origem,
            }
            for s in solicitacoes
        ],
        "total_pendentes": total_pendentes,
    }


@router.put("/solicitacoes/{solicitacao_id}/status")
def atualizar_status_solicitacao(
    solicitacao_id: int,
    dados: SolicitacaoStatusUpdate,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Aprovar ou rejeitar solicitação de cadastro."""
    sol = db.query(models.SolicitacaoCadastro).filter(
        models.SolicitacaoCadastro.id == solicitacao_id
    ).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    if dados.status not in ("aprovado", "rejeitado"):
        raise HTTPException(status_code=400, detail="Status deve ser 'aprovado' ou 'rejeitado'")

    sol.status = dados.status
    if dados.status == "rejeitado" and dados.motivo:
        sol.motivo_rejeicao = dados.motivo
    sol.atualizado_em = datetime.utcnow()
    db.commit()

    return {"sucesso": True, "status": sol.status}


@router.post("/solicitacoes/{solicitacao_id}/criar-restaurante")
async def criar_restaurante_de_solicitacao(
    solicitacao_id: int,
    dados: CriarRestauranteDeSolicitacao,
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Converte solicitação em restaurante real (1-click)."""
    sol = db.query(models.SolicitacaoCadastro).filter(
        models.SolicitacaoCadastro.id == solicitacao_id
    ).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if sol.restaurante_id:
        raise HTTPException(status_code=400, detail="Restaurante já foi criado para esta solicitação")

    # Verificar email duplicado
    email_limpo = sol.email.strip().lower()
    existe_email = db.query(models.Restaurante).filter(
        models.Restaurante.email == email_limpo
    ).first()
    if existe_email:
        raise HTTPException(status_code=400, detail=f"Email {email_limpo} já cadastrado no restaurante '{existe_email.nome_fantasia}'")

    # Verificar CNPJ duplicado (se informado)
    cnpj_limpo = None
    if sol.cnpj:
        cnpj_limpo = re.sub(r'\D', '', sol.cnpj)
        if cnpj_limpo:
            existe_cnpj = db.query(models.Restaurante).filter(
                models.Restaurante.cnpj == cnpj_limpo
            ).first()
            if existe_cnpj:
                raise HTTPException(status_code=400, detail=f"CNPJ já cadastrado no restaurante '{existe_cnpj.nome_fantasia}'")

    # Gerar senha padrão (primeiros 6 dígitos do telefone)
    telefone_limpo = re.sub(r'\D', '', sol.telefone or '')
    senha_padrao = telefone_limpo[:6] if len(telefone_limpo) >= 6 else "123456"

    endereco = dados.endereco_completo.strip() if dados.endereco_completo.strip() else f"{sol.cidade or ''}, {sol.estado or ''}".strip(", ")
    if not endereco:
        endereco = "A definir"

    restaurante = models.Restaurante(
        nome=sol.nome_fantasia,
        nome_fantasia=sol.nome_fantasia,
        cnpj=cnpj_limpo or None,
        email=email_limpo,
        telefone=telefone_limpo,
        endereco_completo=endereco,
        cidade=sol.cidade,
        estado=sol.estado,
        plano=dados.plano,
        valor_plano=dados.valor_plano,
        limite_motoboys=dados.limite_motoboys,
        ativo=True,
        status='ativo',
        data_vencimento=datetime.utcnow() + timedelta(days=30),
    )
    restaurante.gerar_codigo_acesso()
    restaurante.set_senha(senha_padrao)

    db.add(restaurante)
    db.flush()

    # Config padrão
    config = models.ConfigRestaurante(restaurante_id=restaurante.id)
    db.add(config)

    # Site config
    if dados.criar_site:
        site_config = models.SiteConfig(
            restaurante_id=restaurante.id,
            tipo_restaurante=dados.tipo_restaurante or sol.tipo_restaurante or "geral",
        )
        db.add(site_config)

    db.commit()
    db.refresh(restaurante)

    # Seed produtos padrão
    tipo_rest = dados.tipo_restaurante or sol.tipo_restaurante or "geral"
    if dados.criar_site:
        try:
            from database.seed.seed_produtos_padrao import criar_produtos_padrao
            total = criar_produtos_padrao(db, restaurante.id, tipo_rest)
            if total > 0:
                db.commit()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Seed produtos padrão falhou: {e}")
            db.rollback()
            db.refresh(restaurante)

    # Iniciar trial
    trial_dias = 15
    if dados.iniciar_trial:
        try:
            from ..billing.billing_service import iniciar_trial
            await iniciar_trial(restaurante.id, db, admin_id=current_admin.id)
            db.refresh(restaurante)
            config_billing = db.query(models.ConfigBilling).first()
            if config_billing:
                trial_dias = config_billing.trial_dias or 15
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erro ao iniciar trial: {e}")

    # Vincular solicitação
    sol.restaurante_id = restaurante.id
    sol.status = "aprovado"
    sol.atualizado_em = datetime.utcnow()
    db.commit()

    # Enviar email boas-vindas
    email_enviado = False
    if dados.enviar_email and email_limpo:
        try:
            link_painel = f"{BASE_URL}/admin/login"
            link_onboarding = f"{BASE_URL}/admin/inicio"
            resultado_email = await enviar_email_boas_vindas(
                email_destino=email_limpo,
                nome_fantasia=sol.nome_fantasia,
                codigo_acesso=restaurante.codigo_acesso,
                senha_padrao=senha_padrao,
                link_painel=link_painel,
                link_onboarding=link_onboarding,
            )
            email_enviado = resultado_email.get("enviado", False)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erro ao enviar email boas-vindas: {e}")

    return {
        "sucesso": True,
        "restaurante": {
            "id": restaurante.id,
            "nome_fantasia": restaurante.nome_fantasia,
            "email": restaurante.email,
            "codigo_acesso": restaurante.codigo_acesso,
            "senha_padrao": senha_padrao,
            "plano": restaurante.plano,
            "trial_dias": trial_dias,
        },
        "email_enviado": email_enviado,
    }
