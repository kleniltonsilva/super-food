"""
Módulo de Seleção Justa de Motoboys - Super Food SaaS

Implementa algoritmo de seleção inteligente para distribuir entregas
entre motoboys de forma equilibrada.

Critérios de Seleção (filtro rígido, sem fallback):
1. Motoboy deve estar ATIVO e DISPONÍVEL
2. Motoboy NÃO pode estar em rota (em_rota == False E entregas_pendentes == 0)
3. GPS atualizado obrigatório
4. Distância até restaurante ≤ 50 metros (haversine)
5. Score: entregas_hoje × 1000 + ordem_hierarquia + distância × 10
   Quem fez menos no dia = selecionado. Desempate: hierarquia.

Autor: Super Food Team
Versão: 2.0 — Seleção inteligente com GPS e distribuição diária
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.session import get_db_session
from database.models import Motoboy, Restaurante, ConfigRestaurante, Entrega, Pedido
from utils.haversine import haversine


# ==================== FUNÇÕES AUXILIARES ====================

def contar_entregas_dia(motoboy_id: int, session) -> int:
    """
    Conta entregas finalizadas pelo motoboy no dia atual.
    Reutilizável em relatórios e seleção.
    """
    hoje = date.today()
    inicio_dia = datetime.combine(hoje, datetime.min.time())
    status_finalizados = ['entregue', 'cliente_ausente', 'cancelado_cliente']

    count = session.query(Entrega).filter(
        Entrega.motoboy_id == motoboy_id,
        Entrega.status.in_(status_finalizados),
        Entrega.entregue_em >= inicio_dia
    ).count()
    return count


# ==================== SELEÇÃO PRINCIPAL ====================

RAIO_MAXIMO_METROS = 50  # Motoboy deve estar a no máximo 50m do restaurante

def selecionar_motoboy_para_rota(
    restaurante_id: int,
    quantidade_pedidos: int = 1,
    session=None
) -> Optional[Dict]:
    """
    Seleciona o motoboy mais adequado para receber uma nova rota.

    Filtro rígido (sem fallback):
    1. status == 'ativo', disponivel == True
    2. em_rota == False E entregas_pendentes == 0 (finalizou tudo)
    3. GPS atualizado obrigatório (latitude_atual e longitude_atual)
    4. Distância até restaurante ≤ 50 metros

    Score (menor é melhor):
    - entregas_hoje × 1000 + ordem_hierarquia + distância × 10
    - Quem fez menos no dia = selecionado. Desempate: hierarquia.

    Args:
        restaurante_id: ID do restaurante
        quantidade_pedidos: Número de pedidos na rota
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Dict com dados do motoboy selecionado ou None se nenhum disponível
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        # Buscar restaurante para coordenadas
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == restaurante_id
        ).first()

        if not restaurante:
            return None

        # Coordenadas do restaurante são obrigatórias para filtro de distância
        if not restaurante.latitude or not restaurante.longitude:
            return None

        # Filtro rígido: ativo, disponível, NÃO em rota, sem pendências
        motoboys = session.query(Motoboy).filter(
            Motoboy.restaurante_id == restaurante_id,
            Motoboy.status == 'ativo',
            Motoboy.disponivel == True,
            Motoboy.em_rota == False,
            Motoboy.entregas_pendentes <= 0
        ).all()

        if not motoboys:
            return None

        # Calcular score para cada motoboy
        candidatos = []
        for motoboy in motoboys:
            # GPS obrigatório — sem GPS atualizado = não elegível
            if not motoboy.latitude_atual or not motoboy.longitude_atual:
                continue

            # Calcular distância do restaurante em km
            distancia_km = haversine(
                (motoboy.latitude_atual, motoboy.longitude_atual),
                (restaurante.latitude, restaurante.longitude)
            )

            # Filtro de proximidade: ≤ 50 metros (0.05 km)
            distancia_metros = distancia_km * 1000
            if distancia_metros > RAIO_MAXIMO_METROS:
                continue

            # Contar entregas realizadas hoje (distribuição justa)
            entregas_hoje = contar_entregas_dia(motoboy.id, session)

            # Score: menor é melhor
            score = (
                (entregas_hoje * 1000) +         # Prioridade máxima: menos entregas no dia
                (motoboy.ordem_hierarquia or 0) + # Rotação justa
                (distancia_km * 10)               # Proximidade como desempate
            )

            candidatos.append({
                'motoboy': motoboy,
                'score': score,
                'distancia_km': distancia_km,
                'entregas_hoje': entregas_hoje
            })

        if not candidatos:
            return None

        # Ordenar por score (menor primeiro)
        candidatos.sort(key=lambda x: x['score'])

        # Selecionar o melhor candidato
        selecionado = candidatos[0]
        motoboy = selecionado['motoboy']

        # Determinar motivo da seleção
        if len(candidatos) == 1:
            motivo = "Único motoboy elegível no raio de 50m"
        elif selecionado['entregas_hoje'] == 0:
            motivo = "Sem entregas no dia, menor hierarquia"
        else:
            motivo = f"Menos entregas hoje ({selecionado['entregas_hoje']}), score {selecionado['score']:.0f}"

        return {
            'motoboy_id': motoboy.id,
            'nome': motoboy.nome,
            'telefone': motoboy.telefone,
            'ordem_hierarquia': motoboy.ordem_hierarquia or 0,
            'entregas_hoje': selecionado['entregas_hoje'],
            'distancia_restaurante_km': round(selecionado['distancia_km'], 2),
            'motivo_selecao': motivo,
            'total_candidatos': len(candidatos)
        }

    finally:
        if close_session:
            session.close()


# ==================== ATRIBUIR ROTA AO MOTOBOY ====================

def atribuir_rota_motoboy(
    motoboy_id: int,
    pedidos_ids: List[int],
    session=None
) -> Dict:
    """
    Atribui uma rota (lista de pedidos) a um motoboy.

    Atualiza:
    - motoboy.em_rota = True
    - motoboy.entregas_pendentes += len(pedidos)
    - motoboy.ultima_rota_em = agora
    - motoboy.ordem_hierarquia (incrementa para rotação)
    - Cria registros de Entrega para cada pedido

    Args:
        motoboy_id: ID do motoboy
        pedidos_ids: Lista de IDs dos pedidos
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Dict com status da operação
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

        if motoboy.status != 'ativo':
            return {'sucesso': False, 'erro': 'Motoboy não está ativo'}

        # Atualizar motoboy
        motoboy.em_rota = True
        motoboy.entregas_pendentes = (motoboy.entregas_pendentes or 0) + len(pedidos_ids)
        motoboy.ultima_rota_em = datetime.utcnow()

        # Atualizar hierarquia (vai para o final da fila)
        max_hierarquia = session.query(Motoboy).filter(
            Motoboy.restaurante_id == motoboy.restaurante_id,
            Motoboy.status == 'ativo'
        ).count()
        motoboy.ordem_hierarquia = max_hierarquia

        # Criar entregas para cada pedido
        entregas_criadas = []
        for i, pedido_id in enumerate(pedidos_ids):
            pedido = session.query(Pedido).filter(Pedido.id == pedido_id).first()
            if not pedido:
                continue

            # Verificar se já existe entrega para este pedido
            entrega_existente = session.query(Entrega).filter(
                Entrega.pedido_id == pedido_id
            ).first()

            if entrega_existente:
                # Atualizar entrega existente
                entrega_existente.motoboy_id = motoboy_id
                entrega_existente.status = 'em_rota'
                entrega_existente.atribuido_em = datetime.utcnow()
                entrega_existente.posicao_rota_original = i + 1
                entregas_criadas.append(entrega_existente.id)
            else:
                # Criar nova entrega
                entrega = Entrega(
                    pedido_id=pedido_id,
                    motoboy_id=motoboy_id,
                    status='em_rota',
                    atribuido_em=datetime.utcnow(),
                    posicao_rota_original=i + 1,
                    distancia_km=pedido.distancia_restaurante_km
                )
                session.add(entrega)
                session.flush()
                entregas_criadas.append(entrega.id)

            # Atualizar pedido - marca como despachado mas mantém status até motoboy iniciar rota
            pedido.despachado = True
            # Status 'saiu_entrega' será definido quando o motoboy clicar em "Iniciar Rota"

        session.commit()

        return {
            'sucesso': True,
            'motoboy_id': motoboy_id,
            'motoboy_nome': motoboy.nome,
            'quantidade_pedidos': len(pedidos_ids),
            'entregas_ids': entregas_criadas,
            'entregas_pendentes_total': motoboy.entregas_pendentes
        }

    except Exception as e:
        session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


# ==================== FINALIZAR ENTREGA ====================

def finalizar_entrega_motoboy(
    entrega_id: int,
    distancia_km: float = None,
    session=None,
    motivo_finalizacao: str = 'entregue',
    observacao: str = None,
    lat_atual: float = None,
    lon_atual: float = None
) -> Dict:
    """
    Finaliza uma entrega e atualiza estatísticas do motoboy.

    IMPORTANTE: O motoboy SEMPRE recebe o valor da entrega, mesmo em cancelamentos
    ou cliente ausente, pois ele foi até o local e gastou combustível.

    Atualiza:
    - entrega.status = status apropriado baseado no motivo
    - entrega.motivo_finalizacao = motivo
    - entrega.entregue_em = agora
    - motoboy.entregas_pendentes -= 1
    - motoboy.total_entregas += 1
    - motoboy.total_km += distancia
    - motoboy.total_ganhos += valor (SEMPRE, independente do motivo)
    - motoboy.ultima_entrega_em = agora
    - Se entregas_pendentes == 0: motoboy.em_rota = False
    - Calcula e registra ganho do motoboy

    Args:
        entrega_id: ID da entrega
        distancia_km: Distância percorrida (usa valor salvo se None)
        session: Sessão SQLAlchemy (opcional)
        motivo_finalizacao: 'entregue', 'cliente_ausente', 'cancelado_cliente', 'cancelado_restaurante'
        observacao: Observação adicional sobre a finalização

    Returns:
        Dict com status e valores calculados
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        entrega = session.query(Entrega).filter(
            Entrega.id == entrega_id
        ).first()

        if not entrega:
            return {'sucesso': False, 'erro': 'Entrega não encontrada'}

        # Verificar se já foi finalizada (qualquer motivo)
        if entrega.status in ['entregue', 'cliente_ausente', 'cancelado_cliente', 'cancelado_restaurante']:
            return {'sucesso': False, 'erro': 'Entrega já finalizada'}

        motoboy = session.query(Motoboy).filter(
            Motoboy.id == entrega.motoboy_id
        ).first()

        if not motoboy:
            return {'sucesso': False, 'erro': 'Motoboy não encontrado'}

        pedido = session.query(Pedido).filter(
            Pedido.id == entrega.pedido_id
        ).first()

        # Validar raio de 50m se coordenadas fornecidas
        fora_do_raio = False
        if lat_atual is not None and lon_atual is not None and pedido:
            from utils.haversine import haversine
            lat_destino = pedido.latitude_entrega
            lon_destino = pedido.longitude_entrega

            if lat_destino and lon_destino:
                distancia_metros = haversine((lat_atual, lon_atual), (lat_destino, lon_destino)) * 1000
                fora_do_raio = distancia_metros > 50

                if fora_do_raio:
                    # Verificar configuração do restaurante
                    config = session.query(ConfigRestaurante).filter(
                        ConfigRestaurante.restaurante_id == pedido.restaurante_id
                    ).first()

                    if config and not config.permitir_finalizar_fora_raio:
                        return {
                            'sucesso': False,
                            'erro': 'Você está fora do raio de 50m do endereço de entrega. Aproxime-se do destino para finalizar.',
                            'distancia_metros': distancia_metros
                        }

        # Usar distância fornecida ou a salva na entrega
        dist = distancia_km if distancia_km is not None else (entrega.distancia_km or 0)

        # Calcular ganho do motoboy - SEMPRE calcula, independente do motivo
        # O motoboy gastou combustível e tempo indo até o local
        from utils.calculos import calcular_ganho_motoboy
        ganho = calcular_ganho_motoboy(
            pedido.restaurante_id if pedido else motoboy.restaurante_id,
            dist,
            session
        )

        # Determinar status da entrega baseado no motivo
        status_map = {
            'entregue': 'entregue',
            'cliente_ausente': 'cliente_ausente',
            'cancelado_cliente': 'cancelado_cliente',
            'cancelado_restaurante': 'cancelado_restaurante'
        }
        status_entrega = status_map.get(motivo_finalizacao, 'entregue')

        # Atualizar entrega
        entrega.status = status_entrega
        entrega.motivo_finalizacao = motivo_finalizacao
        entrega.entregue_em = datetime.utcnow()
        entrega.delivery_finished_at = datetime.utcnow()
        entrega.finalizado_fora_raio = fora_do_raio
        entrega.distancia_km = dist
        entrega.valor_motoboy = ganho['valor_total']
        entrega.valor_base_motoboy = ganho['valor_base']
        entrega.valor_extra_motoboy = ganho['valor_extra']

        # Salvar observação se fornecida
        if observacao:
            entrega.motivo_cancelamento = observacao

        # Atualizar motoboy - SEMPRE atualiza estatísticas e ganhos
        motoboy.entregas_pendentes = max(0, (motoboy.entregas_pendentes or 1) - 1)
        motoboy.total_entregas = (motoboy.total_entregas or 0) + 1
        motoboy.total_km = (motoboy.total_km or 0) + dist
        motoboy.total_ganhos = (motoboy.total_ganhos or 0) + ganho['valor_total']
        motoboy.ultima_entrega_em = datetime.utcnow()

        # Se não tem mais entregas, sai da rota
        if motoboy.entregas_pendentes == 0:
            motoboy.em_rota = False
            # Atualizar hierarquia para rotação justa
            _atualizar_hierarquia_motoboys(motoboy.restaurante_id, session)

        # Atualizar pedido com status apropriado
        if pedido:
            pedido.status = status_entrega

        session.commit()

        return {
            'sucesso': True,
            'entrega_id': entrega_id,
            'motoboy_id': motoboy.id,
            'distancia_km': dist,
            'valor_ganho': ganho['valor_total'],
            'valor_base': ganho['valor_base'],
            'valor_extra': ganho['valor_extra'],
            'entregas_pendentes': motoboy.entregas_pendentes,
            'em_rota': motoboy.em_rota,
            'motivo_finalizacao': motivo_finalizacao,
            'total_ganhos_dia': _calcular_ganhos_dia(motoboy.id, session)
        }

    except Exception as e:
        session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


# ==================== FUNÇÕES AUXILIARES ====================

def _atualizar_hierarquia_motoboys(restaurante_id: int, session) -> None:
    """
    Atualiza a ordem hierárquica de todos os motoboys ativos.
    Motoboys que finalizaram rota mais recentemente vão para o final.
    """
    motoboys = session.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).order_by(
        Motoboy.ultima_entrega_em.asc().nullsfirst(),
        Motoboy.ordem_hierarquia.asc()
    ).all()

    for i, motoboy in enumerate(motoboys):
        motoboy.ordem_hierarquia = i + 1


def _calcular_ganhos_dia(motoboy_id: int, session) -> float:
    """
    Calcula total de ganhos do motoboy no dia atual.

    IMPORTANTE: Inclui todas as entregas finalizadas, incluindo:
    - entregue: entrega normal
    - cliente_ausente: motoboy foi até o local mas cliente não estava
    - cancelado_cliente: cliente cancelou após motoboy sair

    O motoboy recebe o valor em todos esses casos pois ele foi até o local.
    """
    from datetime import date
    hoje = date.today()

    # Incluir todos os status que geram pagamento ao motoboy
    status_pagos = ['entregue', 'cliente_ausente', 'cancelado_cliente']

    entregas_hoje = session.query(Entrega).filter(
        Entrega.motoboy_id == motoboy_id,
        Entrega.status.in_(status_pagos),
        Entrega.entregue_em >= datetime.combine(hoje, datetime.min.time())
    ).all()

    return sum(e.valor_motoboy or 0 for e in entregas_hoje)


def marcar_motoboy_disponivel(
    motoboy_id: int,
    disponivel: bool = True,
    latitude: float = None,
    longitude: float = None,
    session=None
) -> Dict:
    """
    Marca um motoboy como disponível/indisponível.

    Args:
        motoboy_id: ID do motoboy
        disponivel: True para disponível, False para indisponível
        latitude: Latitude atual (opcional)
        longitude: Longitude atual (opcional)
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Dict com status da operação
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

        motoboy.disponivel = disponivel
        motoboy.ultimo_status_online = datetime.utcnow()

        if latitude and longitude:
            motoboy.latitude_atual = latitude
            motoboy.longitude_atual = longitude
            motoboy.ultima_atualizacao_gps = datetime.utcnow()

        # Se ficou indisponível, atualizar hierarquia
        if not disponivel:
            _atualizar_hierarquia_motoboys(motoboy.restaurante_id, session)

        session.commit()

        return {
            'sucesso': True,
            'motoboy_id': motoboy_id,
            'disponivel': disponivel,
            'ordem_hierarquia': motoboy.ordem_hierarquia
        }

    except Exception as e:
        session.rollback()
        return {'sucesso': False, 'erro': str(e)}

    finally:
        if close_session:
            session.close()


def listar_motoboys_disponiveis(
    restaurante_id: int,
    session=None
) -> List[Dict]:
    """
    Lista todos os motoboys disponíveis para entregas.

    Args:
        restaurante_id: ID do restaurante
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Lista de dicts com dados dos motoboys
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        motoboys = session.query(Motoboy).filter(
            Motoboy.restaurante_id == restaurante_id,
            Motoboy.status == 'ativo',
            Motoboy.disponivel == True
        ).order_by(
            Motoboy.ordem_hierarquia.asc()
        ).all()

        resultado = []
        for m in motoboys:
            resultado.append({
                'id': m.id,
                'nome': m.nome,
                'telefone': m.telefone,
                'disponivel': m.disponivel,
                'em_rota': m.em_rota,
                'entregas_pendentes': m.entregas_pendentes or 0,
                'ordem_hierarquia': m.ordem_hierarquia or 0,
                'capacidade_entregas': m.capacidade_entregas or 3,
                'total_entregas': m.total_entregas or 0,
                'total_ganhos': m.total_ganhos or 0,
                'ultima_entrega': m.ultima_entrega_em.isoformat() if m.ultima_entrega_em else None
            })

        return resultado

    finally:
        if close_session:
            session.close()


def obter_estatisticas_motoboy(
    motoboy_id: int,
    session=None
) -> Dict:
    """
    Obtém estatísticas detalhadas de um motoboy.

    Args:
        motoboy_id: ID do motoboy
        session: Sessão SQLAlchemy (opcional)

    Returns:
        Dict com estatísticas completas
    """
    close_session = session is None
    if session is None:
        session = get_db_session()

    try:
        motoboy = session.query(Motoboy).filter(
            Motoboy.id == motoboy_id
        ).first()

        if not motoboy:
            return None

        # Calcular ganhos do dia
        from datetime import date
        hoje = date.today()

        entregas_hoje = session.query(Entrega).filter(
            Entrega.motoboy_id == motoboy_id,
            Entrega.status == 'entregue',
            Entrega.entregue_em >= datetime.combine(hoje, datetime.min.time())
        ).all()

        ganhos_hoje = sum(e.valor_motoboy or 0 for e in entregas_hoje)
        km_hoje = sum(e.distancia_km or 0 for e in entregas_hoje)

        return {
            'id': motoboy.id,
            'nome': motoboy.nome,
            'status': motoboy.status,
            'disponivel': motoboy.disponivel,
            'em_rota': motoboy.em_rota,
            'entregas_pendentes': motoboy.entregas_pendentes or 0,
            'ordem_hierarquia': motoboy.ordem_hierarquia or 0,
            # Estatísticas totais
            'total_entregas': motoboy.total_entregas or 0,
            'total_ganhos': motoboy.total_ganhos or 0,
            'total_km': motoboy.total_km or 0,
            # Estatísticas do dia
            'entregas_hoje': len(entregas_hoje),
            'ganhos_hoje': round(ganhos_hoje, 2),
            'km_hoje': round(km_hoje, 2),
            # Médias
            'media_por_entrega': round(
                (motoboy.total_ganhos or 0) / max(1, motoboy.total_entregas or 1), 2
            ),
            'media_km_por_entrega': round(
                (motoboy.total_km or 0) / max(1, motoboy.total_entregas or 1), 2
            )
        }

    finally:
        if close_session:
            session.close()


# ==================== EXPORTS ====================

__all__ = [
    'selecionar_motoboy_para_rota',
    'atribuir_rota_motoboy',
    'finalizar_entrega_motoboy',
    'marcar_motoboy_disponivel',
    'listar_motoboys_disponiveis',
    'obter_estatisticas_motoboy',
]
