# backend/app/pix/pix_tasks.py
"""
Task assincrona periodica de Pix.
Verifica restaurantes com saque automatico ativo e executa saques
quando saldo >= valor minimo configurado.

Roda a cada 30 minutos, em paralelo com billing_tasks.
"""

import asyncio
import logging

from ..database import SessionLocal
from .pix_service import executar_saques_automaticos

logger = logging.getLogger("superfood.pix")

INTERVALO_VERIFICACAO = 30 * 60  # 30 minutos


async def verificar_pix_periodico():
    """Task periodica: saque automatico a cada 30 min."""
    # Aguarda 2 minutos para o app estabilizar (migrations, conexoes, etc.)
    await asyncio.sleep(120)

    while True:
        try:
            db = SessionLocal()
            try:
                await executar_saques_automaticos(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro na task de Pix: {e}")

        await asyncio.sleep(INTERVALO_VERIFICACAO)
