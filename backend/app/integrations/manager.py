"""
Orquestrador de integrações com marketplaces.
Gerencia lifecycle de todos os clientes marketplace ativos.
Roda como background task no FastAPI lifespan.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from sqlalchemy.orm import Session

from database import models
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Gerencia todas as integrações marketplace ativas."""

    def __init__(self):
        self._clients: Dict[str, Any] = {}  # key: f"{marketplace}:{restaurante_id}"
        self._polling_task: Optional[asyncio.Task] = None
        self._running = False
        self._app = None  # Referência ao FastAPI app

    def set_app(self, app):
        """Define referência ao app FastAPI para acessar ws_manager, printer_manager."""
        self._app = app

    async def start(self):
        """Inicia o manager e carrega integrações ativas do banco."""
        self._running = True
        logger.info("IntegrationManager: iniciando...")
        self._polling_task = asyncio.create_task(self._polling_loop())
        logger.info("IntegrationManager: polling loop iniciado")

    async def stop(self):
        """Para todos os clientes e o polling loop."""
        self._running = False
        # Parar todos os clientes
        for key, client in self._clients.items():
            try:
                await client.stop()
                logger.info(f"IntegrationManager: cliente {key} parado")
            except Exception as e:
                logger.error(f"IntegrationManager: erro ao parar {key}: {e}")
        self._clients.clear()
        # Cancelar polling task
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("IntegrationManager: parado")

    async def _polling_loop(self):
        """Loop principal: a cada 30s, faz polling de todos os clientes ativos."""
        while self._running:
            try:
                await self._refresh_clients()
                await self._poll_all_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"IntegrationManager: erro no polling loop: {e}")

            # Esperar 30 segundos entre ciclos de polling
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

    async def _refresh_clients(self):
        """Carrega/atualiza clientes baseado nas integrações ativas no banco."""
        db: Session = SessionLocal()
        try:
            integracoes = db.query(models.IntegracaoMarketplace).filter(
                models.IntegracaoMarketplace.ativo == True
            ).all()

            active_keys = set()
            for integ in integracoes:
                key = f"{integ.marketplace}:{integ.restaurante_id}"
                active_keys.add(key)

                if key not in self._clients:
                    client = self._create_client(integ)
                    if client:
                        try:
                            auth_ok = await client.authenticate()
                            if auth_ok:
                                self._clients[key] = client
                                logger.info(f"IntegrationManager: cliente {key} autenticado e adicionado")
                            else:
                                logger.warning(f"IntegrationManager: falha auth para {key}")
                        except Exception as e:
                            logger.error(f"IntegrationManager: erro ao autenticar {key}: {e}")

            # Remover clientes que não estão mais ativos
            removed = set(self._clients.keys()) - active_keys
            for key in removed:
                client = self._clients.pop(key, None)
                if client:
                    try:
                        await client.stop()
                    except Exception:
                        pass
                    logger.info(f"IntegrationManager: cliente {key} removido (desativado)")
        finally:
            db.close()

    def _create_client(self, integ: models.IntegracaoMarketplace):
        """Factory: cria o client correto baseado no tipo de marketplace."""
        config = {
            "client_id": integ.client_id,
            "client_secret": integ.client_secret,
            "merchant_id": integ.merchant_id,
            "access_token": integ.access_token,
            "refresh_token": integ.refresh_token,
            "token_expires_at": integ.token_expires_at,
            "config_json": integ.config_json or {},
        }

        if integ.marketplace == "ifood":
            from .ifood.client import IFoodClient
            return IFoodClient(
                integracao_id=integ.id,
                restaurante_id=integ.restaurante_id,
                config=config,
            )
        elif integ.marketplace in ("99food", "rappi", "keeta"):
            from .opendelivery.client import OpenDeliveryClient
            return OpenDeliveryClient(
                integracao_id=integ.id,
                restaurante_id=integ.restaurante_id,
                config=config,
                marketplace_name=integ.marketplace,
            )
        else:
            logger.warning(f"IntegrationManager: marketplace desconhecido: {integ.marketplace}")
            return None

    async def _poll_all_clients(self):
        """Faz polling de todos os clientes ativos e processa novos pedidos."""
        for key, client in list(self._clients.items()):
            try:
                events = await client.poll_orders()
                if events:
                    await self._process_events(client, events)
            except Exception as e:
                logger.error(f"IntegrationManager: erro polling {key}: {e}")

    async def _process_events(self, client, events: list):
        """Processa eventos recebidos de um marketplace."""
        db: Session = SessionLocal()
        event_ids_to_ack = []
        try:
            for event in events:
                event_id = event.get("id") or event.get("eventId") or event.get("event_id", "")
                event_type = event.get("code") or event.get("type") or event.get("event_type", "")

                # Idempotência: checar se já processamos este evento
                existing = db.query(models.MarketplaceEventLog).filter(
                    models.MarketplaceEventLog.event_id == str(event_id)
                ).first()
                if existing and existing.processed:
                    event_ids_to_ack.append(str(event_id))
                    continue

                # Registrar evento no log
                log_entry = models.MarketplaceEventLog(
                    restaurante_id=client.restaurante_id,
                    marketplace=client.marketplace_name,
                    event_type=str(event_type),
                    event_id=str(event_id),
                    payload_json=event,
                    processed=False,
                )
                if not existing:
                    db.add(log_entry)
                    db.flush()

                try:
                    await self._handle_event(db, client, event, event_type)
                    # Marcar como processado
                    if existing:
                        existing.processed = True
                    else:
                        log_entry.processed = True
                    event_ids_to_ack.append(str(event_id))
                except Exception as e:
                    logger.error(f"IntegrationManager: erro processando evento {event_id}: {e}")
                    if existing:
                        existing.error_message = str(e)
                    else:
                        log_entry.error_message = str(e)

            db.commit()

            # Acknowledge eventos processados
            if event_ids_to_ack:
                try:
                    await client.acknowledge_events(event_ids_to_ack)
                except Exception as e:
                    logger.error(f"IntegrationManager: erro ack eventos: {e}")

        except Exception as e:
            db.rollback()
            logger.error(f"IntegrationManager: erro geral processamento: {e}")
        finally:
            db.close()

    async def _handle_event(self, db: Session, client, event: dict, event_type: str):
        """Processa um evento específico: novo pedido, mudança de status, etc."""
        # Eventos de novo pedido
        if event_type in ("PLACED", "PLC", "NEW", "newOrder", "CREATED"):
            order_data = event.get("order") or event.get("data") or event
            order_id = (
                event.get("orderId")
                or event.get("order_id")
                or order_data.get("id")
                or order_data.get("orderId")
                or ""
            )

            # Verificar se já existe pedido com este marketplace_order_id
            existing_pedido = db.query(models.Pedido).filter(
                models.Pedido.restaurante_id == client.restaurante_id,
                models.Pedido.marketplace_order_id == str(order_id),
            ).first()
            if existing_pedido:
                client._log("info", f"Pedido marketplace {order_id} já existe (id={existing_pedido.id})")
                return

            # Se o evento não contém dados completos do pedido, buscar via API
            if not order_data.get("customer") and not order_data.get("items"):
                full_order = await client.fetch_order_details(str(order_id))
                if full_order:
                    order_data = full_order

            # Mapear pedido marketplace → formato Derekh
            pedido_data = client.map_order_to_pedido(order_data)
            if not pedido_data:
                client._log("error", f"Falha ao mapear pedido {order_id}")
                return

            # Gerar comanda
            from ..routers.painel import _gerar_proxima_comanda
            comanda = _gerar_proxima_comanda(db, client.restaurante_id)

            # Criar pedido
            pedido = models.Pedido(
                restaurante_id=client.restaurante_id,
                comanda=comanda,
                tipo=pedido_data.get("tipo", "delivery"),
                origem="marketplace",
                tipo_entrega=pedido_data.get("tipo_entrega", "entrega"),
                cliente_nome=pedido_data.get("cliente_nome", "Cliente Marketplace"),
                cliente_telefone=pedido_data.get("cliente_telefone"),
                endereco_entrega=pedido_data.get("endereco_entrega"),
                latitude_entrega=pedido_data.get("latitude_entrega"),
                longitude_entrega=pedido_data.get("longitude_entrega"),
                itens=pedido_data.get("itens_texto", "Pedido marketplace"),
                carrinho_json=pedido_data.get("carrinho_json", []),
                observacoes=pedido_data.get("observacoes"),
                valor_total=pedido_data.get("valor_total", 0),
                valor_subtotal=pedido_data.get("valor_subtotal", 0),
                valor_taxa_entrega=pedido_data.get("valor_taxa_entrega", 0),
                valor_desconto=pedido_data.get("valor_desconto", 0),
                forma_pagamento=pedido_data.get("forma_pagamento"),
                status="pendente",
                marketplace_source=client.marketplace_name,
                marketplace_order_id=str(order_id),
                marketplace_display_id=pedido_data.get("marketplace_display_id"),
                marketplace_raw_json=order_data,
            )
            db.add(pedido)
            db.flush()

            client._log("info", f"Novo pedido marketplace criado: id={pedido.id}, comanda={comanda}")

            # Broadcast para admin WS (novo pedido)
            if self._app:
                ws = getattr(self._app.state, 'ws_manager', None)
                if ws:
                    await ws.broadcast({
                        "tipo": "novo_pedido",
                        "dados": {
                            "pedido_id": pedido.id,
                            "comanda": pedido.comanda,
                            "cliente_nome": pedido.cliente_nome,
                            "valor_total": pedido.valor_total,
                            "origem": "marketplace",
                            "marketplace_source": client.marketplace_name,
                        }
                    }, client.restaurante_id)

                # Broadcast para printer agent (impressão automática)
                config = db.query(models.ConfigRestaurante).filter(
                    models.ConfigRestaurante.restaurante_id == client.restaurante_id
                ).first()
                if config and config.impressao_automatica:
                    pm = getattr(self._app.state, 'printer_manager', None)
                    if pm:
                        await pm.broadcast({
                            "tipo": "imprimir_pedido",
                            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
                        }, client.restaurante_id)

            # Auto-confirmar se configurado (iFood requer confirmação)
            if hasattr(client, 'confirm_order'):
                try:
                    await client.confirm_order(str(order_id))
                except Exception as e:
                    client._log("error", f"Falha ao confirmar pedido {order_id}: {e}")

        # Eventos de cancelamento
        elif event_type in ("CANCELLED", "CAN", "CANCELLATION_REQUESTED", "orderCancelled"):
            order_id = event.get("orderId") or event.get("order_id", "")
            pedido = db.query(models.Pedido).filter(
                models.Pedido.restaurante_id == client.restaurante_id,
                models.Pedido.marketplace_order_id == str(order_id),
            ).first()
            if pedido and pedido.status not in ("cancelado", "entregue"):
                pedido.status = "cancelado"
                pedido.observacoes = (pedido.observacoes or "") + f"\n[Cancelado pelo {client.marketplace_name}]"
                client._log("info", f"Pedido {pedido.id} cancelado pelo marketplace")

                # Broadcast cancelamento
                if self._app:
                    ws = getattr(self._app.state, 'ws_manager', None)
                    if ws:
                        await ws.broadcast({
                            "tipo": "pedido_cancelado",
                            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
                        }, client.restaurante_id)

        # Outros eventos (status updates) — log apenas
        else:
            client._log("debug", f"Evento não tratado: {event_type}")

    async def notify_status_change(self, db: Session, pedido: models.Pedido, new_status: str):
        """Chamado quando o admin muda o status de um pedido marketplace.
        Envia a atualização de volta ao marketplace."""
        if not pedido.marketplace_source or not pedido.marketplace_order_id:
            return

        key = f"{pedido.marketplace_source}:{pedido.restaurante_id}"
        client = self._clients.get(key)
        if not client:
            logger.warning(f"IntegrationManager: cliente não encontrado para {key}")
            return

        marketplace_status = client.map_status_to_marketplace(new_status)
        if marketplace_status:
            try:
                await client.update_order_status(
                    pedido.marketplace_order_id,
                    marketplace_status
                )
                client._log("info", f"Status enviado ao marketplace: {new_status} → {marketplace_status}")
            except Exception as e:
                client._log("error", f"Falha ao enviar status: {e}")

    def get_client(self, marketplace: str, restaurante_id: int):
        """Retorna o cliente marketplace para um restaurante, se ativo."""
        key = f"{marketplace}:{restaurante_id}"
        return self._clients.get(key)

    def get_active_integrations(self, restaurante_id: int) -> list:
        """Lista integrações ativas de um restaurante."""
        result = []
        for key, client in self._clients.items():
            if client.restaurante_id == restaurante_id:
                result.append({
                    "marketplace": client.marketplace_name,
                    "running": client.is_running,
                })
        return result


# Instância global (singleton)
integration_manager = IntegrationManager()
