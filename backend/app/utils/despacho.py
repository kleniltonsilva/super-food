"""
Sistema de Despacho Inteligente com Rotas Otimizadas
ATUALIZAÇÃO COMPLETA: Implementa toda lógica descrita (TSP, capacidade, alertas, zona de cobertura)
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys
import os

# Adiciona path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.models import (
    Pedido, Motoboy, Entrega, ConfigRestaurante, 
    RotaOtimizada, Notificacao, Restaurante
)
from utils.tsp_optimizer import otimizar_rota_tsp, calcular_metricas_rota
from utils.mapbox_api import check_coverage_zone


# ==================== FUNÇÕES AUXILIARES ====================

def criar_notificacao(
    db: Session,
    tipo: str,
    titulo: str,
    mensagem: str,
    restaurante_id: Optional[int] = None,
    motoboy_id: Optional[int] = None
):
    """Cria notificação no sistema"""
    notif = Notificacao(
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        restaurante_id=restaurante_id,
        motoboy_id=motoboy_id,
        lida=False,
        data_criacao=datetime.utcnow()
    )
    db.add(notif)
    db.commit()


def validar_endereco_zona_cobertura(
    db: Session,
    restaurante_id: int,
    endereco_cliente: str,
    lat_cliente: float,
    lon_cliente: float
) -> Tuple[bool, str]:
    """
    Valida se o endereço do cliente está na zona de cobertura
    
    Returns:
        (valido: bool, mensagem: str)
    """
    
    # Busca restaurante
    restaurante = db.query(Restaurante).filter(Restaurante.id == restaurante_id).first()
    if not restaurante or not restaurante.latitude or not restaurante.longitude:
        return False, "Coordenadas do restaurante não configuradas"
    
    # Busca config
    config = db.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()
    
    if not config:
        return False, "Configuração do restaurante não encontrada"
    
    raio_maximo = config.raio_entrega_km
    
    # Valida zona de cobertura
    resultado = check_coverage_zone(
        (restaurante.latitude, restaurante.longitude),
        (lat_cliente, lon_cliente),
        raio_maximo
    )
    
    return resultado['dentro_zona'], resultado['mensagem']


def calcular_capacidade_total_motoboys(db: Session, restaurante_id: int) -> Dict:
    """
    Calcula capacidade total de entregas dos motoboys online
    
    Returns:
        {
            'motoboys_online': int,
            'capacidade_total': int,
            'capacidade_disponivel': int,
            'pedidos_em_rota': int
        }
    """
    
    # Busca motoboys ativos (status = 'ativo' significa aprovado e online)
    motoboys = db.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).all()
    
    if not motoboys:
        return {
            'motoboys_online': 0,
            'capacidade_total': 0,
            'capacidade_disponivel': 0,
            'pedidos_em_rota': 0
        }
    
    capacidade_total = sum(m.capacidade_entregas for m in motoboys)
    
    # Conta pedidos em rota
    pedidos_em_rota = db.query(Entrega).join(Pedido).filter(
        Pedido.restaurante_id == restaurante_id,
        Entrega.status.in_(['pendente', 'em_rota'])
    ).count()
    
    capacidade_disponivel = capacidade_total - pedidos_em_rota
    
    return {
        'motoboys_online': len(motoboys),
        'capacidade_total': capacidade_total,
        'capacidade_disponivel': capacidade_disponivel,
        'pedidos_em_rota': pedidos_em_rota
    }


def verificar_pedidos_atrasados(db: Session, restaurante_id: int):
    """
    Marca pedidos como atrasados baseado no tempo estimado
    """
    
    config = db.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()
    
    if not config:
        return
    
    tempo_preparo = config.tempo_medio_preparo
    
    # Busca pedidos pendentes ou em preparo
    pedidos = db.query(Pedido).filter(
        Pedido.restaurante_id == restaurante_id,
        Pedido.status.in_(['pendente', 'em_preparo']),
        Pedido.atrasado == False
    ).all()
    
    agora = datetime.utcnow()
    
    for pedido in pedidos:
        # Calcula tempo decorrido desde criação
        tempo_decorrido = (agora - pedido.data_criacao).total_seconds() / 60  # em minutos
        
        # Se passou do tempo de preparo + tempo estimado de entrega
        tempo_total_permitido = tempo_preparo + (pedido.tempo_estimado or 30)
        
        if tempo_decorrido > tempo_total_permitido:
            pedido.atrasado = True
            
            # Notifica restaurante
            criar_notificacao(
                db,
                tipo='pedido_atrasado',
                titulo='⚠️ Pedido Atrasado',
                mensagem=f'Pedido #{pedido.comanda} está atrasado! Tempo decorrido: {int(tempo_decorrido)} min',
                restaurante_id=restaurante_id
            )
    
    db.commit()


# ==================== DESPACHO AUTOMÁTICO INTELIGENTE ====================

def despachar_pedidos_automatico(db: Session, restaurante_id: int) -> Dict:
    """
    FUNÇÃO PRINCIPAL - Despacho automático inteligente
    
    Lógica completa:
    1. Verifica se despacho automático está ativado
    2. Busca pedidos prontos para despacho
    3. Verifica capacidade de motoboys
    4. Valida zona de cobertura de cada pedido
    5. Otimiza rotas com TSP
    6. Atribui motoboys respeitando capacidade
    7. Cria alertas se necessário
    8. Gerencia pedidos atrasados
    
    Returns:
        {
            'sucesso': bool,
            'mensagem': str,
            'pedidos_despachados': int,
            'rotas_criadas': int,
            'alertas': [...]
        }
    """
    
    # 1. Verifica config
    config = db.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()
    
    if not config:
        return {'sucesso': False, 'mensagem': 'Configuração não encontrada'}
    
    if not config.despacho_automatico:
        return {'sucesso': False, 'mensagem': 'Despacho automático desativado'}
    
    # 2. Verifica pedidos atrasados
    verificar_pedidos_atrasados(db, restaurante_id)
    
    # 3. Busca pedidos prontos para despacho (status = 'pronto' e tipo = 'Entrega')
    pedidos_pendentes = db.query(Pedido).filter(
        Pedido.restaurante_id == restaurante_id,
        Pedido.tipo == 'Entrega',
        Pedido.status == 'pronto',
        Pedido.despachado == False
    ).order_by(Pedido.data_criacao).all()  # Ordem cronológica
    
    if not pedidos_pendentes:
        return {'sucesso': True, 'mensagem': 'Nenhum pedido para despachar', 'pedidos_despachados': 0}
    
    # 4. Verifica capacidade de motoboys
    capacidade = calcular_capacidade_total_motoboys(db, restaurante_id)
    
    if capacidade['motoboys_online'] == 0:
        criar_notificacao(
            db,
            tipo='alerta_capacidade',
            titulo='❌ Nenhum Motoboy Online',
            mensagem=f'{len(pedidos_pendentes)} pedido(s) aguardando despacho, mas nenhum motoboy está online!',
            restaurante_id=restaurante_id
        )
        return {
            'sucesso': False,
            'mensagem': 'Nenhum motoboy online',
            'alertas': ['Nenhum motoboy disponível']
        }
    
    if capacidade['capacidade_disponivel'] < len(pedidos_pendentes):
        criar_notificacao(
            db,
            tipo='alerta_capacidade',
            titulo='⚠️ Capacidade Insuficiente',
            mensagem=f'{len(pedidos_pendentes)} pedidos, mas capacidade disponível é {capacidade["capacidade_disponivel"]}. Alguns pedidos vão atrasar!',
            restaurante_id=restaurante_id
        )
    
    # 5. Busca restaurante (coordenadas)
    restaurante = db.query(Restaurante).filter(Restaurante.id == restaurante_id).first()
    
    if not restaurante or not restaurante.latitude or not restaurante.longitude:
        return {'sucesso': False, 'mensagem': 'Coordenadas do restaurante não configuradas'}
    
    origem_restaurante = (restaurante.latitude, restaurante.longitude)
    
    # 6. Valida zona de cobertura de cada pedido
    pedidos_validos = []
    pedidos_invalidos = []
    
    for pedido in pedidos_pendentes:
        if not pedido.latitude_entrega or not pedido.longitude_entrega:
            pedidos_invalidos.append(f"Pedido #{pedido.comanda}: Coordenadas inválidas")
            continue
        
        dentro_zona, msg = validar_endereco_zona_cobertura(
            db,
            restaurante_id,
            pedido.endereco_entrega,
            pedido.latitude_entrega,
            pedido.longitude_entrega
        )
        
        if not dentro_zona:
            pedidos_invalidos.append(f"Pedido #{pedido.comanda}: {msg}")
            pedido.status = 'cancelado'
            pedido.observacoes = f"{pedido.observacoes or ''}\n[SISTEMA] {msg}"
        else:
            pedidos_validos.append(pedido)
    
    db.commit()
    
    if not pedidos_validos:
        return {
            'sucesso': False,
            'mensagem': 'Todos os pedidos fora da zona de cobertura',
            'alertas': pedidos_invalidos
        }
    
    # 7. Prepara dados para otimização TSP
    destinos_para_otimizar = []
    for pedido in pedidos_validos:
        destinos_para_otimizar.append({
            'pedido_id': pedido.id,
            'lat': pedido.latitude_entrega,
            'lon': pedido.longitude_entrega,
            'comanda': pedido.comanda,
            'tempo_estimado': pedido.tempo_estimado or 30,
            'data_criacao': pedido.data_criacao
        })
    
    # 8. Busca motoboys disponíveis
    motoboys_disponiveis = db.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).all()
    
    # 9. Distribui pedidos entre motoboys respeitando capacidade
    rotas_criadas = 0
    pedidos_despachados = 0
    
    pedidos_restantes = destinos_para_otimizar.copy()
    
    for motoboy in motoboys_disponiveis:
        if not pedidos_restantes:
            break
        
        # Verifica quantos pedidos o motoboy já tem em rota
        pedidos_em_rota = db.query(Entrega).filter(
            Entrega.motoboy_id == motoboy.id,
            Entrega.status.in_(['pendente', 'em_rota'])
        ).count()
        
        vagas_disponiveis = motoboy.capacidade_entregas - pedidos_em_rota
        
        if vagas_disponiveis <= 0:
            continue
        
        # Pega até o limite de vagas disponíveis
        pedidos_para_motoboy = pedidos_restantes[:vagas_disponiveis]
        pedidos_restantes = pedidos_restantes[vagas_disponiveis:]
        
        # Otimiza rota com TSP
        rota_otimizada = otimizar_rota_tsp(origem_restaurante, pedidos_para_motoboy)
        
        # Calcula métricas
        metricas = calcular_metricas_rota(origem_restaurante, rota_otimizada)
        
        # Cria registro de rota otimizada
        rota_db = RotaOtimizada(
            restaurante_id=restaurante_id,
            motoboy_id=motoboy.id,
            total_pedidos=len(rota_otimizada),
            distancia_total_km=metricas['distancia_total_km'],
            tempo_total_min=metricas['tempo_total_min'],
            ordem_entregas=[p['pedido_id'] for p in rota_otimizada],
            status='pendente',
            data_criacao=datetime.utcnow()
        )
        db.add(rota_db)
        db.flush()
        
        # Cria entregas e atribui ao motoboy
        for idx, pedido_otimizado in enumerate(rota_otimizada, start=1):
            pedido_id = pedido_otimizado['pedido_id']
            pedido_db = db.query(Pedido).filter(Pedido.id == pedido_id).first()
            
            if not pedido_db:
                continue
            
            # Atualiza pedido
            pedido_db.despachado = True
            pedido_db.status = 'saiu_entrega'
            pedido_db.ordem_rota = idx
            
            # Cria entrega
            entrega = Entrega(
                pedido_id=pedido_id,
                motoboy_id=motoboy.id,
                status='pendente',
                posicao_rota_original=destinos_para_otimizar.index(pedido_otimizado) + 1,  # Ordem cronológica
                posicao_rota_otimizada=idx,  # Ordem otimizada TSP
                tempo_preparacao=config.tempo_medio_preparo,
                atribuido_em=datetime.utcnow()
            )
            db.add(entrega)
            
            pedidos_despachados += 1
        
        rotas_criadas += 1
        
        # Notifica motoboy
        criar_notificacao(
            db,
            tipo='nova_rota',
            titulo=f'🚀 Nova Rota ({len(rota_otimizada)} entregas)',
            mensagem=f'Rota otimizada com {len(rota_otimizada)} entregas. Distância: {metricas["distancia_total_km"]} km',
            motoboy_id=motoboy.id
        )
    
    db.commit()
    
    # 10. Verifica se sobraram pedidos
    alertas = []
    if pedidos_restantes:
        alertas.append(f'{len(pedidos_restantes)} pedido(s) não foram despachados por falta de capacidade')
        
        criar_notificacao(
            db,
            tipo='alerta_capacidade',
            titulo='⚠️ Pedidos Não Despachados',
            mensagem=f'{len(pedidos_restantes)} pedido(s) aguardando mais motoboys online',
            restaurante_id=restaurante_id
        )
    
    return {
        'sucesso': True,
        'mensagem': f'{pedidos_despachados} pedidos despachados em {rotas_criadas} rota(s)',
        'pedidos_despachados': pedidos_despachados,
        'rotas_criadas': rotas_criadas,
        'alertas': alertas + pedidos_invalidos
    }


# ==================== DESPACHO MANUAL ====================

def atribuir_pedido_manual(
    db: Session,
    pedido_id: int,
    motoboy_id: int,
    operador: str
) -> Dict:
    """
    Atribui pedido manualmente a um motoboy (override automático)
    
    Args:
        pedido_id: ID do pedido
        motoboy_id: ID do motoboy
        operador: Email/nome do operador
    
    Returns:
        {'sucesso': bool, 'mensagem': str}
    """
    
    # Busca pedido
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        return {'sucesso': False, 'mensagem': 'Pedido não encontrado'}
    
    # Busca motoboy
    motoboy = db.query(Motoboy).filter(Motoboy.id == motoboy_id).first()
    if not motoboy:
        return {'sucesso': False, 'mensagem': 'Motoboy não encontrado'}
    
    # Verifica se motoboy pertence ao mesmo restaurante
    if motoboy.restaurante_id != pedido.restaurante_id:
        return {'sucesso': False, 'mensagem': 'Motoboy não pertence a este restaurante'}
    
    # Verifica capacidade do motoboy
    pedidos_em_rota = db.query(Entrega).filter(
        Entrega.motoboy_id == motoboy_id,
        Entrega.status.in_(['pendente', 'em_rota'])
    ).count()
    
    if pedidos_em_rota >= motoboy.capacidade_entregas:
        return {
            'sucesso': False,
            'mensagem': f'Motoboy já está no limite ({motoboy.capacidade_entregas} entregas)'
        }
    
    # Verifica se pedido já foi despachado
    entrega_existente = db.query(Entrega).filter(Entrega.pedido_id == pedido_id).first()
    
    if entrega_existente:
        # Reatribui para novo motoboy
        entrega_existente.motoboy_id = motoboy_id
        entrega_existente.status = 'pendente'
        entrega_existente.atribuido_em = datetime.utcnow()
    else:
        # Cria nova entrega
        entrega = Entrega(
            pedido_id=pedido_id,
            motoboy_id=motoboy_id,
            status='pendente',
            atribuido_em=datetime.utcnow()
        )
        db.add(entrega)
    
    # Atualiza pedido
    pedido.despachado = True
    pedido.status = 'saiu_entrega'
    pedido.observacoes = f"{pedido.observacoes or ''}\n[MANUAL] Atribuído por {operador}"
    
    db.commit()
    
    # Notifica motoboy
    criar_notificacao(
        db,
        tipo='nova_entrega',
        titulo='📦 Nova Entrega (Manual)',
        mensagem=f'Pedido #{pedido.comanda} atribuído manualmente',
        motoboy_id=motoboy_id
    )
    
    return {
        'sucesso': True,
        'mensagem': f'Pedido #{pedido.comanda} atribuído ao motoboy {motoboy.nome}'
    }


# ==================== REATRIBUIÇÃO AUTOMÁTICA (MOTOBOY OFFLINE) ====================

def reatribuir_pedidos_motoboy_offline(
    db: Session,
    motoboy_id: int,
    autorizado_por_operador: bool = False
) -> Dict:
    """
    Reatribui pedidos de um motoboy que ficou offline
    
    Args:
        motoboy_id: ID do motoboy offline
        autorizado_por_operador: Se True, reatribui automaticamente
    
    Returns:
        {'sucesso': bool, 'mensagem': str, 'pedidos_reatribuidos': int}
    """
    
    motoboy = db.query(Motoboy).filter(Motoboy.id == motoboy_id).first()
    if not motoboy:
        return {'sucesso': False, 'mensagem': 'Motoboy não encontrado'}
    
    # Busca entregas pendentes do motoboy
    entregas_pendentes = db.query(Entrega).filter(
        Entrega.motoboy_id == motoboy_id,
        Entrega.status == 'pendente'  # Não iniciou rota ainda
    ).all()
    
    if not entregas_pendentes:
        return {'sucesso': True, 'mensagem': 'Nenhuma entrega pendente', 'pedidos_reatribuidos': 0}
    
    if not autorizado_por_operador:
        # Apenas notifica, não reatribui
        criar_notificacao(
            db,
            tipo='alerta_motoboy_offline',
            titulo=f'⚠️ Motoboy {motoboy.nome} Offline',
            mensagem=f'{len(entregas_pendentes)} entrega(s) pendente(s). Autorize reatribuição ou aguarde motoboy voltar online.',
            restaurante_id=motoboy.restaurante_id
        )
        return {
            'sucesso': False,
            'mensagem': 'Aguardando autorização do operador',
            'pedidos_pendentes': len(entregas_pendentes)
        }
    
    # Reatribui automaticamente
    pedidos_reatribuidos = 0
    
    for entrega in entregas_pendentes:
        # Marca entrega como cancelada
        entrega.status = 'cancelado'
        
        # Volta pedido para pronto
        pedido = db.query(Pedido).filter(Pedido.id == entrega.pedido_id).first()
        if pedido:
            pedido.status = 'pronto'
            pedido.despachado = False
            pedidos_reatribuidos += 1
    
    db.commit()
    
    # Dispara despacho automático novamente
    despachar_pedidos_automatico(db, motoboy.restaurante_id)
    
    return {
        'sucesso': True,
        'mensagem': f'{pedidos_reatribuidos} pedido(s) reatribuído(s)',
        'pedidos_reatribuidos': pedidos_reatribuidos
    }