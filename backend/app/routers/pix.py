# backend/app/routers/pix.py
"""
Endpoints de Pix Online para o painel do restaurante.
Gerencia adesão, saldo, saques e configurações Pix via Woovi/OpenPix.
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from .. import models, database, auth
from ..pix import pix_service

logger = logging.getLogger("superfood.pix")

router = APIRouter(prefix="/painel/pix", tags=["Pix Online"])


# ─── Request/Response Models ──────────────────────────────────────

class AtivarPixRequest(BaseModel):
    pix_chave: str
    tipo_chave: Literal["cpf", "cnpj", "email", "celular", "aleatoria"]
    nome: str
    termos_aceitos: bool

    @field_validator("pix_chave")
    @classmethod
    def validar_chave(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Chave Pix não pode ser vazia")
        return v

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome da subconta não pode ser vazio")
        return v


class ConfigSaqueRequest(BaseModel):
    saque_automatico: bool
    saque_minimo_centavos: int

    @field_validator("saque_minimo_centavos")
    @classmethod
    def validar_minimo(cls, v: int) -> int:
        if v < 100:
            raise ValueError("Valor mínimo de saque deve ser pelo menos R$1,00 (100 centavos)")
        return v


class SaqueRequest(BaseModel):
    valor_centavos: int

    @field_validator("valor_centavos")
    @classmethod
    def validar_valor(cls, v: int) -> int:
        if v < 100:
            raise ValueError("Valor mínimo para saque é R$1,00 (100 centavos)")
        return v


# ─── Endpoints ──────────────────────────────────────────


@router.post("/ativar")
async def ativar_pix(
    dados: AtivarPixRequest,
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Ativa Pix Online para o restaurante. Cria subconta na Woovi."""
    if not dados.termos_aceitos:
        raise HTTPException(
            status_code=400,
            detail="É necessário aceitar os termos para ativar o Pix Online",
        )

    try:
        resultado = await pix_service.ativar_pix(
            restaurante_id=restaurante.id,
            pix_chave=dados.pix_chave,
            tipo_chave=dados.tipo_chave,
            nome=dados.nome,
            db=db,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao ativar Pix para restaurante {restaurante.id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao comunicar com gateway de pagamento: {e}",
        )


@router.get("/status")
async def pix_status(
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Retorna status Pix + saldo + config saque + últimos saques."""
    try:
        return await pix_service.get_pix_status(
            restaurante_id=restaurante.id,
            db=db,
        )
    except Exception as e:
        logger.error(f"Erro ao buscar status Pix do restaurante {restaurante.id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar status Pix: {e}",
        )


@router.post("/desativar")
async def desativar_pix(
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Desativa Pix Online do restaurante (não deleta subconta Woovi)."""
    try:
        resultado = await pix_service.desativar_pix(
            restaurante_id=restaurante.id,
            db=db,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao desativar Pix do restaurante {restaurante.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config-saque")
async def config_saque(
    dados: ConfigSaqueRequest,
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Configura saque automático (ligado/desligado + valor mínimo)."""
    try:
        resultado = await pix_service.atualizar_config_saque(
            restaurante_id=restaurante.id,
            saque_automatico=dados.saque_automatico,
            saque_minimo_centavos=dados.saque_minimo_centavos,
            db=db,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao atualizar config saque do restaurante {restaurante.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sacar")
async def preview_saque(
    dados: SaqueRequest,
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """
    Preview do saque: calcula taxa antes de executar.
    Retorna valor, taxa, valor líquido e se é isento de taxa.
    NÃO executa o saque — usar /sacar/confirmar para isso.
    """
    try:
        saldo = await pix_service.consultar_saldo(
            restaurante_id=restaurante.id,
            db=db,
        )

        if dados.valor_centavos > saldo:
            raise HTTPException(
                status_code=400,
                detail=f"Saldo insuficiente. Disponível: R${saldo / 100:.2f}",
            )

        # Taxa: R$1,00 (100 centavos) para saques < R$500,00 (50000 centavos)
        isento_taxa = dados.valor_centavos >= 50000
        taxa_centavos = 0 if isento_taxa else 100
        valor_liquido_centavos = dados.valor_centavos - taxa_centavos

        return {
            "valor_centavos": dados.valor_centavos,
            "taxa_centavos": taxa_centavos,
            "valor_liquido_centavos": valor_liquido_centavos,
            "isento_taxa": isento_taxa,
            "saldo_atual_centavos": saldo,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao calcular preview saque do restaurante {restaurante.id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar saldo: {e}",
        )


@router.post("/sacar/confirmar")
async def confirmar_saque(
    dados: SaqueRequest,
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
):
    """Executa o saque efetivamente. Usa saque parcial se necessário."""
    try:
        resultado = await pix_service.solicitar_saque(
            restaurante_id=restaurante.id,
            valor_centavos=dados.valor_centavos,
            db=db,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao executar saque do restaurante {restaurante.id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao processar saque: {e}",
        )


@router.get("/saques")
def listar_saques(
    restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista histórico de saques paginado."""
    saques = (
        db.query(models.PixSaque)
        .filter(models.PixSaque.restaurante_id == restaurante.id)
        .order_by(models.PixSaque.solicitado_em.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total = (
        db.query(models.PixSaque)
        .filter(models.PixSaque.restaurante_id == restaurante.id)
        .count()
    )

    return {
        "saques": [
            {
                "id": s.id,
                "valor_centavos": s.valor_centavos,
                "taxa_centavos": s.taxa_centavos,
                "status": s.status,
                "automatico": s.automatico,
                "solicitado_em": s.solicitado_em.isoformat() if s.solicitado_em else None,
                "concluido_em": s.concluido_em.isoformat() if s.concluido_em else None,
            }
            for s in saques
        ],
        "total": total,
    }
