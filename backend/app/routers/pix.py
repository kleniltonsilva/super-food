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
from ..feature_guard import verificar_feature
from ..pix import pix_service

logger = logging.getLogger("superfood.pix")

router = APIRouter(prefix="/painel/pix", tags=["Pix Online"])


# ─── Request/Response Models ──────────────────────────────────────

class AtivarPixRequest(BaseModel):
    termos_aceitos: bool


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


@router.get("/pre-ativacao")
def pre_ativacao_pix(
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
):
    """Retorna dados que serão usados na ativação (CNPJ/CPF + razão social).
    Frontend exibe para o dono confirmar antes de ativar."""
    cnpj = (restaurante.cnpj or "").strip()
    cpf_resp = (getattr(restaurante, "cpf_responsavel", "") or "").strip()
    razao = (restaurante.razao_social or "").strip()
    nome_fantasia = (restaurante.nome_fantasia or restaurante.nome or "").strip()

    if cnpj:
        pix_chave = cnpj
        tipo_chave = "cnpj"
        # Mascarar: 12.345.678/0001-00
        chave_formatada = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}" if len(cnpj) == 14 else cnpj
    elif cpf_resp:
        pix_chave = cpf_resp
        tipo_chave = "cpf"
        chave_formatada = f"{cpf_resp[:3]}.{cpf_resp[3:6]}.{cpf_resp[6:9]}-{cpf_resp[9:]}" if len(cpf_resp) == 11 else cpf_resp
    else:
        return {
            "pode_ativar": False,
            "motivo": "Cadastre o CNPJ da empresa (ou CPF do responsável) "
                      "nas Configurações antes de ativar o Pix Online.",
        }

    return {
        "pode_ativar": True,
        "tipo_chave": tipo_chave,
        "pix_chave_formatada": chave_formatada,
        "nome_subconta": razao or nome_fantasia,
    }


@router.post("/ativar")
async def ativar_pix(
    dados: AtivarPixRequest,
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
    db: Session = Depends(database.get_db),
):
    """Ativa Pix Online para o restaurante. Cria subconta na Woovi.

    A chave Pix é obrigatoriamente o CNPJ da empresa (ou CPF do responsável
    se não houver CNPJ). O nome da subconta é a razão social — não editável.
    """
    if not dados.termos_aceitos:
        raise HTTPException(
            status_code=400,
            detail="É necessário aceitar os termos para ativar o Pix Online",
        )

    # Derivar chave Pix e nome automaticamente do cadastro do restaurante
    cnpj = (restaurante.cnpj or "").strip()
    cpf_resp = (getattr(restaurante, "cpf_responsavel", "") or "").strip()
    razao = (restaurante.razao_social or "").strip()
    nome_fantasia = (restaurante.nome_fantasia or restaurante.nome or "").strip()

    if cnpj:
        pix_chave = cnpj
        tipo_chave = "cnpj"
    elif cpf_resp:
        pix_chave = cpf_resp
        tipo_chave = "cpf"
    else:
        raise HTTPException(
            status_code=400,
            detail="Cadastre o CNPJ da empresa (ou CPF do responsável) "
                   "nas Configurações antes de ativar o Pix Online.",
        )

    nome_subconta = razao or nome_fantasia

    try:
        resultado = await pix_service.ativar_pix(
            restaurante_id=restaurante.id,
            pix_chave=pix_chave,
            tipo_chave=tipo_chave,
            nome=nome_subconta,
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
    restaurante: models.Restaurante = Depends(verificar_feature("pix_online")),
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
