# backend/app/schemas/site_schemas.py

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class SiteInfoPublic(BaseModel):
    restaurante_id: int
    codigo_acesso: str
    nome_fantasia: str
    telefone: str
    endereco_completo: str
    tipo_restaurante: str
    tema_cor_primaria: str
    tema_cor_secundaria: str
    logo_url: Optional[str] = None
    banner_principal_url: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    whatsapp_ativo: bool
    whatsapp_mensagem_padrao: str
    pedido_minimo: float
    tempo_entrega_estimado: int
    tempo_retirada_estimado: int
    aceita_dinheiro: bool
    aceita_cartao: bool
    aceita_pix: bool
    aceita_vale_refeicao: bool
    aceita_agendamento: bool
    status_aberto: bool
    horario_abertura: str
    horario_fechamento: str
    dias_semana_abertos: List[str]

class CategoriaPublic(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    icone: Optional[str] = None
    imagem_url: Optional[str] = None
    ordem_exibicao: int
   
    class Config:
        from_attributes = True

class VariacaoSimples(BaseModel):
    id: int
    tipo_variacao: str
    nome: str
    preco_adicional: float
    estoque_disponivel: bool

class ProdutoPublic(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    preco: float
    preco_promocional: Optional[float] = None
    imagem_url: Optional[str] = None
    destaque: bool
    promocao: bool
    categoria_id: Optional[int] = None
    variacoes: List[VariacaoSimples] = []

class ProdutoDetalhadoPublic(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    preco: float
    preco_promocional: Optional[float] = None
    imagem_url: Optional[str] = None
    imagens_adicionais: List[str] = []
    destaque: bool
    promocao: bool
    categoria_id: Optional[int] = None
    variacoes_agrupadas: Dict[str, List[dict]]

class ValidacaoEntregaRequest(BaseModel):
    endereco_texto: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ValidacaoEntregaResponse(BaseModel):
    dentro_zona: bool
    distancia_km: float
    tempo_estimado_min: int
    taxa_entrega: float
    mensagem: str