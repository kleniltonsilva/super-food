# arquivo: backend/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import string
import os
from dotenv import load_dotenv

from db.database import DBManager
from utils.mapbox import geocode
from utils.haversine import haversine
from passlib.context import CryptContext
from datetime import datetime

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(
    title="Gerenciador de Motoboys - API",
    description="API para gestão completa de frota própria de entregas com multi-restaurante",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DBManager()

limites_plano = {"basico": 3, "medio": 5, "premium": 12}

# ================== Modelos ==================
class RestauranteCreate(BaseModel):
    nome: str
    endereco: str
    plano: str = "basico"

class RestauranteResponse(BaseModel):
    id: int
    nome: str
    endereco: str
    plano: str
    codigo_acesso: str
    ativo: bool

class MotoboyCreate(BaseModel):
    restaurante_id: int
    nome: str

class RegisterMotoboy(BaseModel):
    codigo_acesso: str
    nome: str
    sobrenome: Optional[str] = ""
    username: str
    senha: str

class LoginMotoboyUsername(BaseModel):
    username: str
    senha: str

class LoginMotoboyCodigo(BaseModel):
    codigo_acesso: str

class PedidoCreate(BaseModel):
    restaurante_id: int
    comanda: str
    tipo: str
    cliente_nome: str
    cliente_telefone: str
    endereco_entrega: Optional[str] = None
    numero_mesa: Optional[str] = None
    itens: str
    observacoes: str = ""
    tempo_estimado: int

class GPSUpdate(BaseModel):
    motoboy_id: int
    latitude: float
    longitude: float

# ================== Rotas ==================
@app.get("/")
def home():
    return {"mensagem": "API Gerenciador de Motoboys rodando! Acesse /docs para testar as rotas."}

@app.get("/restaurantes/", response_model=List[RestauranteResponse])
def listar_restaurantes():
    db.cursor.execute("SELECT id, nome, endereco, plano, codigo_acesso, ativo FROM restaurantes")
    rows = db.cursor.fetchall()
    return [
        {
            "id": r[0],
            "nome": r[1],
            "endereco": r[2],
            "plano": r[3],
            "codigo_acesso": r[4] or "",
            "ativo": bool(r[5])
        } for r in rows
    ]

@app.post("/restaurantes/", response_model=RestauranteResponse)
def criar_restaurante(rest: RestauranteCreate):
    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db.cursor.execute("""
        INSERT INTO restaurantes (nome, endereco, plano, codigo_acesso, ativo)
        VALUES (?, ?, ?, ?, 1)
    """, (rest.nome, rest.endereco, rest.plano, codigo))
    db.conn.commit()
    rest_id = db.cursor.lastrowid

    coords = geocode(rest.endereco)
    if coords:
        lng, lat = coords
        db.cursor.execute("UPDATE restaurantes SET latitude = ?, longitude = ? WHERE id = ?", (lat, lng, rest_id))
        db.conn.commit()

    return {"id": rest_id, "nome": rest.nome, "endereco": rest.endereco, "plano": rest.plano, "codigo_acesso": codigo, "ativo": True}

@app.get("/motoboys/{restaurante_id}", response_model=List[dict])
def listar_motoboys(restaurante_id: int):
    db.cursor.execute("SELECT id, nome, status FROM motoboys WHERE restaurante_id = ? ORDER BY nome", (restaurante_id,))
    rows = db.cursor.fetchall()
    return [{"id": row[0], "nome": row[1], "status": row[2] or "disponivel"} for row in rows]

@app.post("/motoboys/")
def cadastrar_motoboy_simples(moto: MotoboyCreate):
    db.cursor.execute("SELECT plano FROM restaurantes WHERE id = ?", (moto.restaurante_id,))
    row = db.cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    plano = row[0]

    limite = limites_plano.get(plano, 3)
    db.cursor.execute("SELECT COUNT(*) FROM motoboys WHERE restaurante_id = ?", (moto.restaurante_id,))
    count = db.cursor.fetchone()[0]
    if count >= limite:
        raise HTTPException(status_code=400, detail="Limite de motoboys atingido para este plano")

    db.cursor.execute("""
        INSERT INTO motoboys (nome, restaurante_id, status, max_pedidos_concurrentes) 
        VALUES (?, ?, 'disponivel', 3)
    """, (moto.nome, moto.restaurante_id))
    db.conn.commit()
    return {"id": db.cursor.lastrowid, "nome": moto.nome, "status": "disponivel", "mensagem": "Cadastrado com sucesso"}

@app.post("/motoboys/register/")
def register_motoboy(reg: RegisterMotoboy):
    db.cursor.execute("SELECT id, plano FROM restaurantes WHERE codigo_acesso = ? AND ativo = 1", (reg.codigo_acesso,))
    row = db.cursor.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Código de acesso inválido")
    restaurante_id, plano = row

    limite = limites_plano.get(plano, 3)
    db.cursor.execute("SELECT COUNT(*) FROM motoboys WHERE restaurante_id = ?", (restaurante_id,))
    if db.cursor.fetchone()[0] >= limite:
        raise HTTPException(status_code=400, detail="Limite de motoboys atingido")

    db.cursor.execute("SELECT 1 FROM motoboys WHERE username = ?", (reg.username,))
    if db.cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username já está em uso")

    hashed = pwd_context.hash(reg.senha)
    db.cursor.execute("""
        INSERT INTO motoboys 
        (restaurante_id, nome, sobrenome, username, senha_hash, status, max_pedidos_concurrentes)
        VALUES (?, ?, ?, ?, ?, 'disponivel', 3)
    """, (restaurante_id, reg.nome, reg.sobrenome, reg.username, hashed))
    db.conn.commit()
    return {"mensagem": "Cadastro com login realizado", "motoboy_id": db.cursor.lastrowid}

@app.post("/motoboys/login_username/")
def login_username(login: LoginMotoboyUsername):
    db.cursor.execute("SELECT id, nome, restaurante_id, senha_hash FROM motoboys WHERE username = ?", (login.username,))
    row = db.cursor.fetchone()
    if not row or not pwd_context.verify(login.senha, row[3]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"motoboy_id": row[0], "nome": row[1], "restaurante_id": row[2]}

@app.post("/motoboys/login/")
def login_motoboy_codigo(login: LoginMotoboyCodigo):
    db.cursor.execute("""
        SELECT m.id, m.nome FROM motoboys m
        JOIN restaurantes r ON m.restaurante_id = r.id
        WHERE r.codigo_acesso = ?
    """, (login.codigo_acesso,))
    row = db.cursor.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Código inválido ou nenhum motoboy cadastrado")
    return {"motoboy_id": row[0], "nome": row[1]}

@app.post("/pedidos/")
def criar_pedido(pedido: PedidoCreate):
    data_criacao = datetime.now().isoformat()
    db.cursor.execute("""
        INSERT INTO pedidos (
            restaurante_id, comanda, tipo, cliente_nome, cliente_telefone,
            endereco_entrega, numero_mesa, itens, observacoes, data_criacao, tempo_estimado, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'novo')
    """, (
        pedido.restaurante_id, pedido.comanda, pedido.tipo, pedido.cliente_nome, pedido.cliente_telefone,
        pedido.endereco_entrega, pedido.numero_mesa, pedido.itens, pedido.observacoes, data_criacao, pedido.tempo_estimado
    ))
    db.conn.commit()
    return {"id": db.cursor.lastrowid, "mensagem": "Pedido criado com sucesso"}

@app.get("/pedidos/{restaurante_id}")
def listar_pedidos(restaurante_id: int):
    db.cursor.execute("""
        SELECT id, comanda, tipo, cliente_nome, status, tempo_estimado, data_criacao
        FROM pedidos WHERE restaurante_id = ? ORDER BY id DESC
    """, (restaurante_id,))
    rows = db.cursor.fetchall()
    return [
        {
            "id": row[0],
            "comanda": row[1],
            "tipo": row[2],
            "cliente": row[3],
            "status": row[4],
            "tempo_estimado": row[5],
            "data_criacao": row[6]
        } for row in rows
    ]

@app.get("/pedidos/motoboy/{motoboy_id}")
def pedidos_motoboy(motoboy_id: int):
    db.cursor.execute("""
        SELECT id, comanda, tipo, cliente_nome, endereco_entrega, itens, observacoes, tempo_estimado, status
        FROM pedidos WHERE motoboy_id = ? AND status IN ('despachado', 'em_entrega')
        ORDER BY id DESC
    """, (motoboy_id,))
    rows = db.cursor.fetchall()
    return [
        {
            "id": row[0],
            "comanda": row[1],
            "tipo": row[2],
            "cliente": row[3],
            "endereco": row[4],
            "itens": row[5],
            "observacoes": row[6],
            "tempo_estimado": row[7],
            "status": row[8]
        } for row in rows
    ]

@app.post("/pedidos/despachar/{pedido_id}")
def despachar_pedido(pedido_id: int):
    db.cursor.execute("SELECT tipo, endereco_entrega, restaurante_id FROM pedidos WHERE id = ?", (pedido_id,))
    pedido = db.cursor.fetchone()
    if not pedido or pedido[0] != "Entrega":
        raise HTTPException(status_code=400, detail="Pedido inválido ou não é de Entrega")

    restaurante_id = pedido[2]

    # Coordenadas do restaurante (geocodifica se necessário)
    db.cursor.execute("SELECT latitude, longitude, endereco FROM restaurantes WHERE id = ?", (restaurante_id,))
    rest_row = db.cursor.fetchone()
    if not rest_row[0] or not rest_row[1]:
        coords = geocode(rest_row[2])
        if not coords:
            raise HTTPException(status_code=500, detail="Não foi possível geocodificar endereço do restaurante")
        lat, lng = coords[1], coords[0]
        db.cursor.execute("UPDATE restaurantes SET latitude = ?, longitude = ? WHERE id = ?", (lat, lng, restaurante_id))
        db.conn.commit()
    else:
        lat, lng = rest_row[0], rest_row[1]

    # Busca motoboys com GPS + limite concurrente
    db.cursor.execute("""
        SELECT id, status, latitude, longitude, COALESCE(max_pedidos_concurrentes, 3)
        FROM motoboys 
        WHERE restaurante_id = ? AND latitude IS NOT NULL
    """, (restaurante_id,))
    candidatos_raw = db.cursor.fetchall()
    if not candidatos_raw:
        raise HTTPException(status_code=400, detail="Nenhum motoboy com posição GPS")

    candidatos = []
    for m in candidatos_raw:
        motoboy_id = m[0]
        db.cursor.execute("""
            SELECT COUNT(*) FROM pedidos 
            WHERE motoboy_id = ? AND status IN ('despachado', 'em_entrega')
        """, (motoboy_id,))
        pedidos_ativos = db.cursor.fetchone()[0]
        vagas = m[4] - pedidos_ativos
        if vagas > 0:
            dist = haversine(lat, lng, m[2], m[3])
            candidatos.append({
                "id": motoboy_id,
                "dist": dist,
                "vagas": vagas,
                "disponivel": m[1] == "disponivel"
            })

    if not candidatos:
        raise HTTPException(status_code=400, detail="Todos os motoboys estão no limite de pedidos concurrentes")

    # Prioridade: disponível > menor distância
    candidatos.sort(key=lambda x: (not x["disponivel"], x["dist"]))
    escolhido = candidatos[0]["id"]

    db.cursor.execute("UPDATE pedidos SET motoboy_id = ?, status = 'despachado' WHERE id = ?", (escolhido, pedido_id))
    db.cursor.execute("UPDATE motoboys SET status = 'em_entrega' WHERE id = ?", (escolhido,))
    db.conn.commit()

    return {"mensagem": "Pedido despachado (com limite concurrente respeitado)", "motoboy_id": escolhido}

@app.post("/motoboys/gps/")
def atualizar_gps(gps: GPSUpdate):
    db.cursor.execute("SELECT 1 FROM motoboys WHERE id = ?", (gps.motoboy_id,))
    if not db.cursor.fetchone():
        raise HTTPException(status_code=404, detail="Motoboy não encontrado")
    db.cursor.execute("UPDATE motoboys SET latitude = ?, longitude = ? WHERE id = ?", (gps.latitude, gps.longitude, gps.motoboy_id))
    db.conn.commit()
    return {"mensagem": "GPS atualizado com sucesso"}

@app.get("/motoboys/gps/{restaurante_id}")
def get_gps_motoboys(restaurante_id: int):
    db.cursor.execute("""
        SELECT id, nome, latitude, longitude, status 
        FROM motoboys 
        WHERE restaurante_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
    """, (restaurante_id,))
    rows = db.cursor.fetchall()
    return [{"id": r[0], "nome": r[1], "lat": r[2], "lng": r[3], "status": r[4]} for r in rows]