"""
Módulo de Cálculos - Super Food SaaS

Centraliza toda lógica de cálculos do sistema:
- Taxa de entrega (cobrada do cliente)
- Ganhos do motoboy
- Distâncias e tempos
- Detecção de cidade

Usa Mapbox API com fallback para Haversine.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, date

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.session import get_db_session
from database.models import ConfigRestaurante, Restaurante, Entrega, Motoboy, Pedido
from utils.mapbox_api import (
    geocode_address,
    get_directions,
    get_distance,
    calcular_distancia_tempo,
    MAPBOX_TOKEN
)
from utils.haversine import haversine


# ==================== CÁLCULO DE TAXA DE ENTREGA (CLIENTE) ====================

def calcular_taxa_entrega(
    restaurante_id: int,
    distancia_km: float,
    session=None
) -> Dict:
    """
    Calcula a taxa de entrega a ser cobrada do cliente.

    Args:
        restaurante_id: ID do restaurante
        distancia_km: Distância em km até o cliente
        session: Sessão SQLAlchemy (opcional, cria uma nova se não fornecida)

    Returns:
        {
            'taxa_total': float,      # Valor total da taxa
            'taxa_base': float,       # Parte base da taxa
            'taxa_extra': float,      # Parte extra (km adicionais)
            'distancia_km': float,    # Distância usada no cálculo
            'km_extras': float,       # Km além do base
            'config': dict            # Configuração usada
        }
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante_id
        ).first()

        if not config:
            return {
                'taxa_total': 0.0,
                'taxa_base': 0.0,
                'taxa_extra': 0.0,
                'distancia_km': distancia_km,
                'km_extras': 0.0,
                'config': None,
                'erro': 'Configuração não encontrada'
            }

        taxa_base = config.taxa_entrega_base or 0.0
        distancia_base = config.distancia_base_km or 0.0
        valor_km_extra = config.taxa_km_extra or 0.0

        if distancia_km <= distancia_base:
            taxa_total = taxa_base
            taxa_extra = 0.0
            km_extras = 0.0
        else:
            km_extras = distancia_km - distancia_base
            taxa_extra = km_extras * valor_km_extra
            taxa_total = taxa_base + taxa_extra

        return {
            'taxa_total': round(taxa_total, 2),
            'taxa_base': round(taxa_base, 2),
            'taxa_extra': round(taxa_extra, 2),
            'distancia_km': round(distancia_km, 2),
            'km_extras': round(km_extras, 2),
            'config': {
                'taxa_entrega_base': taxa_base,
                'distancia_base_km': distancia_base,
                'taxa_km_extra': valor_km_extra
            }
        }

    finally:
        if close_session:
            session.close()


# ==================== CÁLCULO DE GANHO DO MOTOBOY ====================

def calcular_ganho_motoboy(
    restaurante_id: int,
    distancia_km: float,
    session=None
) -> Dict:
    """
    Calcula o ganho do motoboy por uma entrega.

    Args:
        restaurante_id: ID do restaurante
        distancia_km: Distância em km da entrega
        session: Sessão SQLAlchemy (opcional)

    Returns:
        {
            'valor_total': float,       # Valor total a pagar
            'valor_base': float,        # Parte base
            'valor_extra': float,       # Parte extra (km adicionais)
            'distancia_km': float,      # Distância usada
            'km_extras': float,         # Km além do base
            'config': dict              # Configuração usada
        }
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante_id
        ).first()

        if not config:
            return {
                'valor_total': 0.0,
                'valor_base': 0.0,
                'valor_extra': 0.0,
                'distancia_km': distancia_km,
                'km_extras': 0.0,
                'config': None,
                'erro': 'Configuração não encontrada'
            }

        valor_base = config.valor_base_motoboy or 0.0
        distancia_base = config.distancia_base_motoboy_km or 0.0
        valor_km_extra = config.valor_km_extra_motoboy or 0.0

        if distancia_km <= distancia_base:
            valor_total = valor_base
            valor_extra = 0.0
            km_extras = 0.0
        else:
            km_extras = distancia_km - distancia_base
            valor_extra = km_extras * valor_km_extra
            valor_total = valor_base + valor_extra

        return {
            'valor_total': round(valor_total, 2),
            'valor_base': round(valor_base, 2),
            'valor_extra': round(valor_extra, 2),
            'distancia_km': round(distancia_km, 2),
            'km_extras': round(km_extras, 2),
            'config': {
                'valor_base_motoboy': valor_base,
                'distancia_base_motoboy_km': distancia_base,
                'valor_km_extra_motoboy': valor_km_extra
            }
        }

    finally:
        if close_session:
            session.close()


# ==================== ATUALIZAR GANHOS DO MOTOBOY ====================

def registrar_ganho_motoboy(
    entrega_id: int,
    distancia_km: float,
    session=None
) -> Dict:
    """
    Registra o ganho do motoboy ao finalizar uma entrega.

    Atualiza:
    - entregas.valor_motoboy
    - entregas.distancia_km
    - motoboys.total_ganhos
    - motoboys.total_entregas

    Args:
        entrega_id: ID da entrega
        distancia_km: Distância percorrida
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Dict com valores calculados e status
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        # Buscar entrega
        entrega = session.query(Entrega).filter(
            Entrega.id == entrega_id
        ).first()

        if not entrega:
            return {'sucesso': False, 'erro': 'Entrega não encontrada'}

        if not entrega.motoboy_id:
            return {'sucesso': False, 'erro': 'Entrega sem motoboy atribuído'}

        # Buscar pedido para obter restaurante_id
        pedido = session.query(Pedido).filter(
            Pedido.id == entrega.pedido_id
        ).first()

        if not pedido:
            return {'sucesso': False, 'erro': 'Pedido não encontrado'}

        # Calcular ganho
        ganho = calcular_ganho_motoboy(pedido.restaurante_id, distancia_km, session)

        if 'erro' in ganho:
            return {'sucesso': False, 'erro': ganho['erro']}

        # Atualizar entrega
        entrega.distancia_km = distancia_km
        entrega.valor_motoboy = ganho['valor_total']
        entrega.valor_base_motoboy = ganho['valor_base']
        entrega.valor_extra_motoboy = ganho['valor_extra']

        # Atualizar motoboy
        motoboy = session.query(Motoboy).filter(
            Motoboy.id == entrega.motoboy_id
        ).first()

        if motoboy:
            motoboy.total_ganhos = (motoboy.total_ganhos or 0) + ganho['valor_total']
            motoboy.total_entregas = (motoboy.total_entregas or 0) + 1

        session.commit()

        return {
            'sucesso': True,
            'valor_motoboy': ganho['valor_total'],
            'distancia_km': distancia_km,
            'motoboy_id': entrega.motoboy_id,
            'total_ganhos_motoboy': motoboy.total_ganhos if motoboy else 0,
            'total_entregas_motoboy': motoboy.total_entregas if motoboy else 0
        }

    except Exception as e:
        session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


# ==================== GANHOS DO DIA (PARA APP MOTOBOY) ====================

def obter_ganhos_dia_motoboy(
    motoboy_id: int,
    data: date = None,
    session=None
) -> Dict:
    """
    Obtém os ganhos do motoboy em um dia específico.

    IMPORTANTE: Inclui todas as entregas finalizadas que geram pagamento:
    - entregue: entrega normal
    - cliente_ausente: motoboy foi até o local mas cliente não estava
    - cancelado_cliente: cliente cancelou após motoboy sair

    O motoboy recebe o valor em todos esses casos pois foi até o local.

    Args:
        motoboy_id: ID do motoboy
        data: Data para consulta (padrão: hoje)
        session: Sessão SQLAlchemy (opcional)

    Returns:
        {
            'total_ganhos': float,
            'total_entregas': int,
            'total_km': float,
            'entregas': list  # Lista de entregas do dia
        }
    """
    if data is None:
        data = date.today()

    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        # Status que geram pagamento ao motoboy
        status_pagos = ['entregue', 'cliente_ausente', 'cancelado_cliente']

        # Buscar entregas do dia (todos os status que geram pagamento)
        entregas = session.query(Entrega).filter(
            Entrega.motoboy_id == motoboy_id,
            Entrega.status.in_(status_pagos),
            Entrega.entregue_em >= datetime.combine(data, datetime.min.time()),
            Entrega.entregue_em < datetime.combine(data, datetime.max.time())
        ).all()

        total_ganhos = sum(e.valor_motoboy or 0 for e in entregas)
        total_km = sum(e.distancia_km or 0 for e in entregas)

        entregas_lista = []
        for e in entregas:
            pedido = session.query(Pedido).filter(Pedido.id == e.pedido_id).first()
            entregas_lista.append({
                'id': e.id,
                'pedido_id': e.pedido_id,
                'endereco': pedido.endereco_entrega if pedido else '',
                'valor': e.valor_motoboy or 0,
                'distancia_km': e.distancia_km or 0,
                'horario': e.entregue_em.strftime('%H:%M') if e.entregue_em else '',
                'status': e.status,
                'motivo_finalizacao': e.motivo_finalizacao
            })

        return {
            'total_ganhos': round(total_ganhos, 2),
            'total_entregas': len(entregas),
            'total_km': round(total_km, 2),
            'data': data.isoformat(),
            'entregas': entregas_lista
        }

    finally:
        if close_session:
            session.close()


# ==================== DETECÇÃO DE CIDADE ====================

def detectar_cidade_endereco(endereco: str) -> Optional[Dict]:
    """
    Detecta a cidade de um endereço usando geocoding reverso.

    Args:
        endereco: Endereço completo

    Returns:
        {
            'cidade': str,
            'estado': str,
            'pais': str,
            'coordenadas': (lat, lng)
        }
        ou None se não conseguir detectar
    """
    if not endereco or not MAPBOX_TOKEN:
        return None

    coords = geocode_address(endereco)
    if not coords:
        return None

    # Geocoding reverso para obter detalhes
    from urllib.parse import quote
    import requests

    lat, lng = coords
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "types": "place,region,country",
        "language": "pt"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        cidade = None
        estado = None
        pais = None
        pais_codigo = None

        for feature in data.get("features", []):
            place_type = feature.get("place_type", [])

            if "place" in place_type:
                cidade = feature.get("text")
            elif "region" in place_type:
                estado = feature.get("text")
                # Tenta pegar a sigla do estado/região
                props = feature.get("properties", {})
                if props.get("short_code"):
                    # Remove prefixo de país (BR-, PT-, US-, etc.)
                    code = props["short_code"]
                    if "-" in code:
                        estado = code.split("-", 1)[1]
                    else:
                        estado = code
            elif "country" in place_type:
                pais = feature.get("text")
                props = feature.get("properties", {})
                pais_codigo = (props.get("short_code") or "").upper()

        return {
            'cidade': cidade,
            'estado': estado,
            'pais': pais,
            'pais_codigo': pais_codigo,
            'coordenadas': coords
        }

    except Exception as e:
        print(f"[WARNING] Falha ao detectar cidade: {e}")
        return None


def atualizar_cidade_restaurante(restaurante_id: int, session=None) -> bool:
    """
    Atualiza cidade e estado do restaurante baseado no endereço.

    Args:
        restaurante_id: ID do restaurante
        session: Sessão SQLAlchemy (opcional)

    Returns:
        True se atualizou com sucesso
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == restaurante_id
        ).first()

        if not restaurante or not restaurante.endereco_completo:
            return False

        info = detectar_cidade_endereco(restaurante.endereco_completo)
        if not info:
            return False

        if info.get('cidade'):
            restaurante.cidade = info['cidade']
        if info.get('estado'):
            restaurante.estado = info['estado']
        if info.get('coordenadas'):
            restaurante.latitude, restaurante.longitude = info['coordenadas']

        session.commit()
        return True

    except Exception as e:
        print(f"[ERRO] Falha ao atualizar cidade: {e}")
        session.rollback()
        return False

    finally:
        if close_session:
            session.close()


def atualizar_coordenadas_restaurante(
    restaurante_id: int,
    novo_endereco: str = None,
    session=None
) -> Dict:
    """
    Atualiza as coordenadas do restaurante via geocodificação.

    IMPORTANTE: Esta função deve ser chamada sempre que o endereço do
    restaurante for alterado, para garantir que os cálculos de distância
    usem coordenadas atualizadas.

    Args:
        restaurante_id: ID do restaurante
        novo_endereco: Novo endereço (se None, usa o atual)
        session: Sessão SQLAlchemy (opcional)

    Returns:
        {
            'sucesso': bool,
            'latitude': float,
            'longitude': float,
            'cidade': str,
            'estado': str,
            'erro': str (se falhou)
        }
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == restaurante_id
        ).first()

        if not restaurante:
            return {'sucesso': False, 'erro': 'Restaurante não encontrado'}

        # Usar novo endereço se fornecido
        endereco = novo_endereco or restaurante.endereco_completo

        if not endereco:
            return {'sucesso': False, 'erro': 'Endereço não informado'}

        # Geocodificar endereço
        coords = geocode_address(endereco)

        if not coords:
            return {'sucesso': False, 'erro': 'Não foi possível geocodificar o endereço'}

        lat, lng = coords

        # Atualizar endereço se fornecido novo
        if novo_endereco:
            restaurante.endereco_completo = novo_endereco

        # Atualizar coordenadas
        restaurante.latitude = lat
        restaurante.longitude = lng

        # Tentar detectar cidade/estado
        info = detectar_cidade_endereco(endereco)
        if info:
            if info.get('cidade'):
                restaurante.cidade = info['cidade']
            if info.get('estado'):
                restaurante.estado = info['estado']

        session.commit()

        return {
            'sucesso': True,
            'latitude': lat,
            'longitude': lng,
            'cidade': restaurante.cidade,
            'estado': restaurante.estado,
            'endereco': endereco
        }

    except Exception as e:
        if session:
            session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


def obter_coordenadas_restaurante_atualizadas(
    restaurante_id: int,
    session=None
) -> Optional[Tuple[float, float]]:
    """
    Obtém coordenadas atualizadas do restaurante.

    Se as coordenadas não existirem, tenta geocodificar o endereço.

    Args:
        restaurante_id: ID do restaurante
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Tuple (latitude, longitude) ou None se falhou
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == restaurante_id
        ).first()

        if not restaurante:
            return None

        # Se já tem coordenadas, retorna
        if restaurante.latitude and restaurante.longitude:
            return (restaurante.latitude, restaurante.longitude)

        # Tentar geocodificar
        if restaurante.endereco_completo:
            coords = geocode_address(restaurante.endereco_completo)
            if coords:
                # Atualizar no banco para cache
                restaurante.latitude, restaurante.longitude = coords
                session.commit()
                return coords

        return None

    finally:
        if close_session:
            session.close()


# ==================== CÁLCULO COMPLETO DE ENTREGA ====================

def calcular_entrega_completa(
    restaurante_id: int,
    endereco_cliente: str,
    session=None
) -> Dict:
    """
    Calcula todos os valores de uma entrega de forma completa.

    IMPORTANTE: Sempre busca coordenadas atualizadas do restaurante,
    garantindo que cálculos reflitam qualquer mudança de endereço.

    Args:
        restaurante_id: ID do restaurante
        endereco_cliente: Endereço de entrega

    Returns:
        {
            'sucesso': bool,
            'distancia_km': float,
            'tempo_estimado_min': int,
            'taxa_cliente': dict,      # Resultado de calcular_taxa_entrega
            'ganho_motoboy': dict,     # Resultado de calcular_ganho_motoboy
            'coordenadas_cliente': (lat, lng),
            'dentro_zona': bool
        }
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        # Buscar restaurante
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == restaurante_id
        ).first()

        if not restaurante:
            return {'sucesso': False, 'erro': 'Restaurante não encontrado'}

        # Buscar config
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante_id
        ).first()

        # SEMPRE buscar coordenadas atualizadas do restaurante
        # Isso garante que mudanças de endereço sejam refletidas
        coords_restaurante = obter_coordenadas_restaurante_atualizadas(restaurante_id, session)

        if not coords_restaurante:
            # Fallback: tentar geocodificar direto
            if restaurante.endereco_completo:
                coords_restaurante = geocode_address(restaurante.endereco_completo)
                if coords_restaurante:
                    # Salvar para cache futuro
                    restaurante.latitude, restaurante.longitude = coords_restaurante
                    session.commit()

        coords_cliente = geocode_address(endereco_cliente)

        if not coords_restaurante or not coords_cliente:
            return {'sucesso': False, 'erro': 'Não foi possível geocodificar endereços'}

        # Calcular distância e tempo
        rota = get_directions(coords_restaurante, coords_cliente)

        if rota:
            distancia_km = round(rota['distance'] / 1000, 2)
            tempo_min = round(rota['duration'] / 60)
        else:
            # Fallback Haversine
            distancia_km = round(haversine(coords_restaurante, coords_cliente), 2)
            tempo_min = round(distancia_km / 0.4)  # ~25 km/h

        # Verificar zona de cobertura
        raio_maximo = config.raio_entrega_km if config else 15.0
        dentro_zona = distancia_km <= raio_maximo

        # Calcular taxa e ganho
        taxa_cliente = calcular_taxa_entrega(restaurante_id, distancia_km, session)
        ganho_motoboy = calcular_ganho_motoboy(restaurante_id, distancia_km, session)

        return {
            'sucesso': True,
            'distancia_km': distancia_km,
            'tempo_estimado_min': tempo_min,
            'taxa_cliente': taxa_cliente,
            'ganho_motoboy': ganho_motoboy,
            'coordenadas_cliente': coords_cliente,
            'coordenadas_restaurante': coords_restaurante,
            'dentro_zona': dentro_zona,
            'raio_maximo_km': raio_maximo
        }

    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


# ==================== RECONCILIAÇÃO DE GANHOS ====================

def reconciliar_ganhos_motoboy(
    motoboy_id: int,
    session=None
) -> Dict:
    """
    Reconcilia os ganhos totais do motoboy com base nas entregas reais.

    Esta função corrige possíveis inconsistências entre:
    - Motoboy.total_ganhos (acumulado)
    - Soma real das entregas finalizadas

    Args:
        motoboy_id: ID do motoboy
        session: Sessão SQLAlchemy (opcional)

    Returns:
        {
            'sucesso': bool,
            'ganhos_anteriores': float,
            'ganhos_calculados': float,
            'diferenca': float,
            'corrigido': bool
        }
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        motoboy = session.query(Motoboy).filter(
            Motoboy.id == motoboy_id
        ).first()

        if not motoboy:
            return {'sucesso': False, 'erro': 'Motoboy não encontrado'}

        # Status que geram pagamento ao motoboy
        status_pagos = ['entregue', 'cliente_ausente', 'cancelado_cliente']

        # Calcular soma real das entregas
        entregas = session.query(Entrega).filter(
            Entrega.motoboy_id == motoboy_id,
            Entrega.status.in_(status_pagos)
        ).all()

        ganhos_calculados = sum(e.valor_motoboy or 0 for e in entregas)
        entregas_contadas = len(entregas)
        km_total = sum(e.distancia_km or 0 for e in entregas)

        ganhos_anteriores = motoboy.total_ganhos or 0
        diferenca = ganhos_calculados - ganhos_anteriores

        # Atualizar se houver diferença significativa (> R$ 0.01)
        corrigido = False
        if abs(diferenca) > 0.01:
            motoboy.total_ganhos = round(ganhos_calculados, 2)
            motoboy.total_entregas = entregas_contadas
            motoboy.total_km = round(km_total, 2)
            session.commit()
            corrigido = True

        return {
            'sucesso': True,
            'ganhos_anteriores': round(ganhos_anteriores, 2),
            'ganhos_calculados': round(ganhos_calculados, 2),
            'diferenca': round(diferenca, 2),
            'total_entregas': entregas_contadas,
            'total_km': round(km_total, 2),
            'corrigido': corrigido
        }

    except Exception as e:
        if session:
            session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


# ==================== EXPORTS ====================

__all__ = [
    'calcular_taxa_entrega',
    'calcular_ganho_motoboy',
    'registrar_ganho_motoboy',
    'obter_ganhos_dia_motoboy',
    'detectar_cidade_endereco',
    'atualizar_cidade_restaurante',
    'atualizar_coordenadas_restaurante',
    'obter_coordenadas_restaurante_atualizadas',
    'calcular_entrega_completa',
    'reconciliar_ganhos_motoboy',
]
