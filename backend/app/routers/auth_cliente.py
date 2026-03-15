# backend/app/routers/auth_cliente.py

"""
Router Auth Cliente - Autenticação, perfil, endereços e pedidos do cliente
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

from .. import models, database
from ..schemas import cliente_schemas

# ==================== CONFIG ====================

SECRET_KEY = os.getenv("SECRET_KEY", "superfood-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72  # 3 dias

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth/cliente", tags=["Auth Cliente"])


# ==================== HELPERS ====================

def hash_senha(senha: str) -> str:
    """Hash bcrypt da senha. Aplica strip() para ignorar espaços acidentais."""
    return pwd_context.hash(senha.strip())


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica senha bcrypt. Aplica strip() para consistência com hash_senha."""
    return pwd_context.verify(senha.strip(), senha_hash)


def criar_token(cliente_id: int, restaurante_id: int) -> str:
    payload = {
        "sub": str(cliente_id),
        "restaurante_id": restaurante_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_cliente_atual(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(database.get_db)
) -> models.Cliente:
    """Dependency: extrai cliente do token JWT"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação necessário")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        cliente_id = int(payload.get("sub", 0))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    cliente = db.query(models.Cliente).filter(
        models.Cliente.id == cliente_id,
        models.Cliente.ativo == True
    ).first()

    if not cliente:
        raise HTTPException(status_code=401, detail="Cliente não encontrado")

    return cliente


def get_cliente_opcional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(database.get_db)
) -> Optional[models.Cliente]:
    """Dependency: retorna cliente se logado, None se não"""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        cliente_id = int(payload.get("sub", 0))
    except (JWTError, ValueError, TypeError):
        return None

    return db.query(models.Cliente).filter(
        models.Cliente.id == cliente_id,
        models.Cliente.ativo == True
    ).first()


# ==================== AUTH ENDPOINTS ====================

@router.post("/registro", response_model=cliente_schemas.TokenResponse)
def registrar_cliente(
    dados: cliente_schemas.ClienteCadastroRequest,
    db: Session = Depends(database.get_db)
):
    """Cadastro de novo cliente"""
    # Busca restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_acesso_restaurante.upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Verifica se email já existe neste restaurante
    existente = db.query(models.Cliente).filter(
        models.Cliente.email == dados.email,
        models.Cliente.restaurante_id == restaurante.id
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado neste restaurante")

    # Cria cliente
    cliente = models.Cliente(
        restaurante_id=restaurante.id,
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        senha_hash=hash_senha(dados.senha),
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        data_cadastro=datetime.utcnow(),
        ultimo_acesso=datetime.utcnow()
    )

    db.add(cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email já cadastrado. Tente fazer login.")
    db.refresh(cliente)

    token = criar_token(cliente.id, restaurante.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "cliente": cliente
    }


@router.post("/login", response_model=cliente_schemas.TokenResponse)
def login_cliente(
    dados: cliente_schemas.ClienteLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do cliente"""
    # Busca restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_acesso_restaurante.upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Busca cliente
    cliente = db.query(models.Cliente).filter(
        models.Cliente.email == dados.email,
        models.Cliente.restaurante_id == restaurante.id,
        models.Cliente.ativo == True
    ).first()

    if not cliente or not verificar_senha(dados.senha, cliente.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Atualiza último acesso
    cliente.ultimo_acesso = datetime.utcnow()
    db.commit()

    token = criar_token(cliente.id, restaurante.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "cliente": cliente
    }


@router.post("/registro-pos-pedido", response_model=cliente_schemas.TokenResponse)
def registro_pos_pedido(
    dados: cliente_schemas.RegistroPosPedidoRequest,
    db: Session = Depends(database.get_db)
):
    """Registro pós-pedido: cria cliente e vincula pedido anônimo"""
    # Busca restaurante pelo código de acesso
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_acesso_restaurante.upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Verifica se email já existe
    existente = db.query(models.Cliente).filter(
        models.Cliente.email == dados.email,
        models.Cliente.restaurante_id == restaurante.id
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    # Cria cliente
    cliente = models.Cliente(
        restaurante_id=restaurante.id,
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        senha_hash=hash_senha(dados.senha),
        data_cadastro=datetime.utcnow(),
        ultimo_acesso=datetime.utcnow()
    )

    db.add(cliente)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email já cadastrado. Tente fazer login.")

    # Vincula pedido ao cliente
    if dados.pedido_id:
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == dados.pedido_id,
            models.Pedido.restaurante_id == restaurante.id,
            models.Pedido.cliente_id == None
        ).first()

        if pedido:
            pedido.cliente_id = cliente.id
            pedido.cliente_nome = cliente.nome
            pedido.cliente_telefone = cliente.telefone

    db.commit()
    db.refresh(cliente)

    token = criar_token(cliente.id, restaurante.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "cliente": cliente
    }


@router.get("/me", response_model=cliente_schemas.ClienteResponse)
def get_perfil(
    cliente: models.Cliente = Depends(get_cliente_atual)
):
    """Retorna dados do cliente logado"""
    return cliente


@router.put("/perfil", response_model=cliente_schemas.ClienteResponse)
def atualizar_perfil(
    dados: cliente_schemas.ClientePerfilUpdate,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Atualiza dados do perfil"""
    if dados.nome is not None:
        cliente.nome = dados.nome
    if dados.telefone is not None:
        cliente.telefone = dados.telefone
    if dados.cpf is not None:
        cliente.cpf = dados.cpf
    if dados.data_nascimento is not None:
        cliente.data_nascimento = dados.data_nascimento

    db.commit()
    db.refresh(cliente)
    return cliente


# ==================== ENDERECOS ====================

@router.get("/enderecos", response_model=List[cliente_schemas.EnderecoResponse])
def listar_enderecos(
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Lista endereços do cliente"""
    enderecos = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.ativo == True
    ).order_by(models.EnderecoCliente.padrao.desc()).all()

    return enderecos


@router.post("/enderecos", response_model=cliente_schemas.EnderecoResponse)
def criar_endereco(
    dados: cliente_schemas.EnderecoCreateRequest,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Adiciona novo endereço"""
    # Se é padrão, remove padrão dos outros
    if dados.padrao:
        db.query(models.EnderecoCliente).filter(
            models.EnderecoCliente.cliente_id == cliente.id
        ).update({"padrao": False})

    endereco = models.EnderecoCliente(
        cliente_id=cliente.id,
        apelido=dados.apelido,
        cep=dados.cep,
        endereco_completo=dados.endereco_completo,
        numero=dados.numero,
        complemento=dados.complemento,
        bairro=dados.bairro,
        cidade=dados.cidade,
        estado=dados.estado,
        referencia=dados.referencia,
        latitude=dados.latitude,
        longitude=dados.longitude,
        padrao=dados.padrao or False
    )

    db.add(endereco)
    db.commit()
    db.refresh(endereco)
    return endereco


@router.put("/enderecos/{endereco_id}", response_model=cliente_schemas.EnderecoResponse)
def atualizar_endereco(
    endereco_id: int,
    dados: cliente_schemas.EnderecoUpdateRequest,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Atualiza endereço existente"""
    endereco = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.id == endereco_id,
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.ativo == True
    ).first()

    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Se marcando como padrão, remove padrão dos outros
    if dados.padrao:
        db.query(models.EnderecoCliente).filter(
            models.EnderecoCliente.cliente_id == cliente.id,
            models.EnderecoCliente.id != endereco_id
        ).update({"padrao": False})

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(endereco, campo, valor)

    db.commit()
    db.refresh(endereco)
    return endereco


@router.delete("/enderecos/{endereco_id}")
def remover_endereco(
    endereco_id: int,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Remove endereço (soft delete)"""
    endereco = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.id == endereco_id,
        models.EnderecoCliente.cliente_id == cliente.id
    ).first()

    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    endereco.ativo = False
    db.commit()

    return {"mensagem": "Endereço removido com sucesso"}


@router.put("/enderecos/{endereco_id}/padrao")
def definir_endereco_padrao(
    endereco_id: int,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Define endereço como padrão"""
    endereco = db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.id == endereco_id,
        models.EnderecoCliente.cliente_id == cliente.id,
        models.EnderecoCliente.ativo == True
    ).first()

    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Remove padrão de todos
    db.query(models.EnderecoCliente).filter(
        models.EnderecoCliente.cliente_id == cliente.id
    ).update({"padrao": False})

    endereco.padrao = True
    db.commit()

    return {"mensagem": "Endereço definido como padrão"}


# ==================== PEDIDOS DO CLIENTE ====================

@router.get("/pedidos", response_model=List[cliente_schemas.PedidoClienteResponse])
def listar_pedidos(
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Lista pedidos do cliente logado"""
    pedidos = db.query(models.Pedido).filter(
        models.Pedido.cliente_id == cliente.id,
        models.Pedido.restaurante_id == cliente.restaurante_id
    ).order_by(models.Pedido.data_criacao.desc()).limit(50).all()

    resultado = []
    for p in pedidos:
        resultado.append({
            "id": p.id,
            "comanda": p.comanda,
            "status": p.status,
            "tipo": p.tipo,
            "tipo_entrega": p.tipo_entrega,
            "endereco_entrega": p.endereco_entrega,
            "valor_total": p.valor_total,
            "forma_pagamento": p.forma_pagamento,
            "observacoes": p.observacoes,
            "data_criacao": p.data_criacao,
            "itens_texto": p.itens,
            "carrinho_json": p.carrinho_json
        })

    return resultado


@router.get("/pedidos/{pedido_id}", response_model=cliente_schemas.PedidoClienteResponse)
def get_pedido_detalhe(
    pedido_id: int,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Detalhe de um pedido do cliente"""
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.cliente_id == cliente.id
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return {
        "id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "tipo": pedido.tipo,
        "tipo_entrega": pedido.tipo_entrega,
        "endereco_entrega": pedido.endereco_entrega,
        "valor_total": pedido.valor_total,
        "forma_pagamento": pedido.forma_pagamento,
        "observacoes": pedido.observacoes,
        "data_criacao": pedido.data_criacao,
        "itens_texto": pedido.itens,
        "carrinho_json": pedido.carrinho_json
    }
