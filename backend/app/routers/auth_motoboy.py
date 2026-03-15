# backend/app/routers/auth_motoboy.py

"""
Router Auth Motoboy - Login, perfil, senha
Sprint 3 da migração v4.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from .. import models, database, auth

# Motoboys precisam de sessão longa — ficam sem internet, app fica em background
MOTOBOY_TOKEN_DAYS = 30

router = APIRouter(prefix="/auth/motoboy", tags=["Auth Motoboy"])


# ========== Schemas ==========

class MotoboyLoginRequest(BaseModel):
    codigo_restaurante: str
    usuario: str
    senha: str


class MotoboyLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    motoboy: dict
    restaurante: dict


class MotoboyMeResponse(BaseModel):
    id: int
    nome: str
    usuario: str
    telefone: str
    cpf: Optional[str] = None
    status: str
    disponivel: bool
    em_rota: bool
    entregas_pendentes: int
    ordem_hierarquia: int
    capacidade_entregas: int
    total_entregas: int
    total_ganhos: float
    total_km: float
    latitude_atual: Optional[float] = None
    longitude_atual: Optional[float] = None
    ultima_atualizacao_gps: Optional[datetime] = None
    ultimo_status_online: Optional[datetime] = None
    ultima_entrega_em: Optional[datetime] = None
    data_cadastro: Optional[datetime] = None
    restaurante: dict

    class Config:
        from_attributes = True


class MotoboySenhaUpdate(BaseModel):
    senha_atual: str
    nova_senha: str


class MotoboyCadastroRequest(BaseModel):
    codigo_acesso: str
    nome: str
    usuario: str
    telefone: str
    cpf: Optional[str] = None


# ========== Endpoints ==========

@router.post("/login", response_model=MotoboyLoginResponse)
def login_motoboy(
    dados: MotoboyLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do motoboy por código do restaurante + usuário + senha. Retorna JWT + dados."""
    # Validar restaurante pelo código de acesso
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_restaurante.strip(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código do restaurante inválido"
        )

    # Buscar motoboy por usuario + restaurante
    motoboy = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == restaurante.id,
        models.Motoboy.usuario == dados.usuario.strip().lower(),
        models.Motoboy.status == 'ativo'
    ).first()

    if not motoboy or not motoboy.verificar_senha(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos"
        )

    # Marcar como disponível e online
    motoboy.disponivel = True
    motoboy.ultimo_status_online = datetime.utcnow()
    db.commit()

    # Gerar JWT com role motoboy — 30 dias para não deslogar durante uso diário
    token = auth.create_access_token(
        data={
            "sub": str(motoboy.id),
            "role": "motoboy",
            "restaurante_id": restaurante.id
        },
        expires_delta=timedelta(days=MOTOBOY_TOKEN_DAYS)
    )

    return MotoboyLoginResponse(
        access_token=token,
        motoboy={
            "id": motoboy.id,
            "nome": motoboy.nome,
            "usuario": motoboy.usuario,
            "telefone": motoboy.telefone,
            "disponivel": motoboy.disponivel,
            "em_rota": motoboy.em_rota or False,
            "entregas_pendentes": motoboy.entregas_pendentes or 0,
            "total_entregas": motoboy.total_entregas or 0,
            "total_ganhos": motoboy.total_ganhos or 0,
        },
        restaurante={
            "id": restaurante.id,
            "nome": restaurante.nome,
            "nome_fantasia": restaurante.nome_fantasia,
            "codigo_acesso": restaurante.codigo_acesso,
            "logo_url": restaurante.logo_url if hasattr(restaurante, 'logo_url') else None,
            "telefone": restaurante.telefone,
            "endereco_completo": restaurante.endereco_completo,
        }
    )


@router.get("/me", response_model=MotoboyMeResponse)
def me_motoboy(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
):
    """Retorna dados completos do motoboy logado + info do restaurante."""
    rest = current_motoboy.restaurante
    return MotoboyMeResponse(
        id=current_motoboy.id,
        nome=current_motoboy.nome,
        usuario=current_motoboy.usuario,
        telefone=current_motoboy.telefone,
        cpf=current_motoboy.cpf,
        status=current_motoboy.status,
        disponivel=current_motoboy.disponivel or False,
        em_rota=current_motoboy.em_rota or False,
        entregas_pendentes=current_motoboy.entregas_pendentes or 0,
        ordem_hierarquia=current_motoboy.ordem_hierarquia or 0,
        capacidade_entregas=current_motoboy.capacidade_entregas or 3,
        total_entregas=current_motoboy.total_entregas or 0,
        total_ganhos=current_motoboy.total_ganhos or 0,
        total_km=current_motoboy.total_km or 0,
        latitude_atual=current_motoboy.latitude_atual,
        longitude_atual=current_motoboy.longitude_atual,
        ultima_atualizacao_gps=current_motoboy.ultima_atualizacao_gps,
        ultimo_status_online=current_motoboy.ultimo_status_online,
        ultima_entrega_em=current_motoboy.ultima_entrega_em,
        data_cadastro=current_motoboy.data_cadastro,
        restaurante={
            "id": rest.id,
            "nome": rest.nome,
            "nome_fantasia": rest.nome_fantasia,
            "codigo_acesso": rest.codigo_acesso,
            "telefone": rest.telefone,
            "endereco_completo": rest.endereco_completo,
            "logo_url": rest.logo_url if hasattr(rest, 'logo_url') else None,
            "latitude": rest.latitude,
            "longitude": rest.longitude,
        }
    )


@router.post("/refresh")
def refresh_token_motoboy(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
):
    """
    Renova o token JWT do motoboy sem precisar de login.
    Chamado automaticamente pelo app quando o token está próximo do vencimento.
    Retorna um novo token com mais 30 dias a partir de agora.
    """
    new_token = auth.create_access_token(
        data={
            "sub": str(current_motoboy.id),
            "role": "motoboy",
            "restaurante_id": current_motoboy.restaurante_id
        },
        expires_delta=timedelta(days=MOTOBOY_TOKEN_DAYS)
    )
    return {"access_token": new_token, "token_type": "bearer"}


@router.put("/senha")
def alterar_senha_motoboy(
    dados: MotoboySenhaUpdate,
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Altera a senha do motoboy."""
    if not current_motoboy.verificar_senha(dados.senha_atual):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if len(dados.nova_senha.strip()) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter no mínimo 6 caracteres")

    current_motoboy.set_senha(dados.nova_senha)
    db.commit()

    return {"mensagem": "Senha alterada com sucesso"}


@router.post("/cadastro")
def cadastro_motoboy(
    dados: MotoboyCadastroRequest,
    db: Session = Depends(database.get_db)
):
    """Solicita cadastro de motoboy (cria MotoboySolicitacao pendente)."""
    codigo_limpo = dados.codigo_acesso.strip().upper()
    nome_limpo = dados.nome.strip()
    usuario_limpo = dados.usuario.strip().lower()
    telefone_limpo = ''.join(filter(str.isdigit, dados.telefone.strip()))

    # Validações
    if len(codigo_limpo) != 8:
        raise HTTPException(status_code=400, detail="Código de acesso deve ter 8 dígitos")
    if len(nome_limpo) < 3:
        raise HTTPException(status_code=400, detail="Nome deve ter pelo menos 3 caracteres")
    if len(usuario_limpo) < 3:
        raise HTTPException(status_code=400, detail="Usuário deve ter pelo menos 3 caracteres")
    if len(telefone_limpo) < 10:
        raise HTTPException(status_code=400, detail="Telefone inválido (mínimo 10 dígitos)")

    # Validar CPF se fornecido
    cpf_limpo = None
    if dados.cpf:
        from utils.cpf import validar_cpf
        cpf_limpo = ''.join(filter(str.isdigit, dados.cpf.strip()))
        if not validar_cpf(cpf_limpo):
            raise HTTPException(status_code=400, detail="CPF inválido")

    # Verificar restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_limpo,
        models.Restaurante.ativo == True
    ).first()
    if not restaurante:
        raise HTTPException(status_code=400, detail="Código do restaurante inválido")

    # Verificar duplicação
    motoboy_existente = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == restaurante.id,
        models.Motoboy.usuario == usuario_limpo
    ).first()
    if motoboy_existente:
        raise HTTPException(status_code=400, detail="Já existe um motoboy com este usuário neste restaurante")

    # Verificar solicitação pendente
    solic_pendente = db.query(models.MotoboySolicitacao).filter(
        models.MotoboySolicitacao.restaurante_id == restaurante.id,
        models.MotoboySolicitacao.usuario == usuario_limpo,
        models.MotoboySolicitacao.status == 'pendente'
    ).first()
    if solic_pendente:
        raise HTTPException(status_code=400, detail="Já existe uma solicitação pendente para este usuário")

    # Criar solicitação
    solicitacao = models.MotoboySolicitacao(
        restaurante_id=restaurante.id,
        nome=nome_limpo,
        usuario=usuario_limpo,
        telefone=telefone_limpo,
        codigo_acesso=codigo_limpo,
        status='pendente',
        data_solicitacao=datetime.utcnow()
    )
    db.add(solicitacao)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma solicitação para este usuário")

    return {
        "mensagem": "Solicitação enviada com sucesso! Aguarde aprovação do restaurante.",
        "info": f"Quando aprovado, use: Código: {codigo_limpo} | Usuário: {usuario_limpo} | Senha: 123456"
    }
