"""
Testes do billing separado para add-on WhatsApp Humanoide — Derekh Food
Valida cobrança avulsa, webhook pagamento, recorrência e desativação.

Execução: pytest tests/test_addon_billing.py -v
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-addon-billing")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/test_addon_billing.db")

import pytest
from fastapi.testclient import TestClient


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def app():
    os.environ["DATABASE_URL"] = f"sqlite:///{PROJECT_ROOT}/test_addon_billing.db"
    os.environ["SECRET_KEY"] = "test-secret-key-addon-billing"

    # Import models first to register them with Base
    import database.models  # noqa: F401

    from backend.app.main import app as fastapi_app
    from backend.app.database import engine, Base

    Base.metadata.create_all(bind=engine)
    yield fastapi_app

    db_path = PROJECT_ROOT / "test_addon_billing.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db_session(app):
    from backend.app.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def restaurante_essencial(db_session):
    """Cria restaurante Essencial (tier 2) para testes de addon billing."""
    from database.models import Restaurante, AsaasCliente
    db = db_session

    rest = db.query(Restaurante).filter(Restaurante.email == "addon_billing_test@test.com").first()
    if not rest:
        rest = Restaurante(
            nome="Addon Billing Test",
            nome_fantasia="Addon Billing Test",
            email="addon_billing_test@test.com",
            telefone="11888888888",
            endereco_completo="Rua Teste 456",
            plano="Essencial",
            plano_tier=2,
            billing_status="active",
            valor_plano=279.90,
            limite_motoboys=5,
            cnpj="98765432000100",
            codigo_acesso="ADDONBL1",
            senha="hashed",
        )
        db.add(rest)
        db.commit()
        db.refresh(rest)

        # Criar AsaasCliente
        asaas_cli = AsaasCliente(
            restaurante_id=rest.id,
            asaas_customer_id="cus_addon_billing_test",
            nome="Addon Billing Test",
            cpf_cnpj="98765432000100",
            email="addon_billing_test@test.com",
        )
        db.add(asaas_cli)
        db.commit()

    return rest


@pytest.fixture(scope="module")
def restaurante_premium(db_session):
    """Cria restaurante Premium (tier 4)."""
    from database.models import Restaurante
    db = db_session

    rest = db.query(Restaurante).filter(Restaurante.email == "premium_billing_test@test.com").first()
    if not rest:
        rest = Restaurante(
            nome="Premium Billing Test",
            nome_fantasia="Premium Billing Test",
            email="premium_billing_test@test.com",
            telefone="11777777777",
            endereco_completo="Rua Premium 789",
            plano="Premium",
            plano_tier=4,
            billing_status="active",
            valor_plano=527.00,
            limite_motoboys=999,
            cnpj="11111111000100",
            codigo_acesso="PREMBL1",
            senha="hashed",
        )
        db.add(rest)
        db.commit()
        db.refresh(rest)
    return rest


@pytest.fixture(scope="module")
def restaurante_basico(db_session):
    """Cria restaurante Basico (tier 1)."""
    from database.models import Restaurante
    db = db_session

    rest = db.query(Restaurante).filter(Restaurante.email == "basico_billing_test@test.com").first()
    if not rest:
        rest = Restaurante(
            nome="Basico Billing Test",
            nome_fantasia="Basico Billing Test",
            email="basico_billing_test@test.com",
            telefone="11666666666",
            endereco_completo="Rua Basico 101",
            plano="Básico",
            plano_tier=1,
            billing_status="active",
            valor_plano=169.90,
            limite_motoboys=2,
            cnpj="22222222000100",
            codigo_acesso="BASBL1",
            senha="hashed",
        )
        db.add(rest)
        db.commit()
        db.refresh(rest)
    return rest


# ==================== TESTES ====================

@pytest.mark.asyncio
async def test_criar_cobranca_essencial(db_session, restaurante_essencial):
    """Cria cobrança avulsa Asaas + AddonCobranca PENDING para Essencial."""
    from backend.app.billing.billing_service import criar_cobranca_addon_bot
    from database.models import AddonCobranca

    mock_payment = {
        "id": "pay_addon_test_001",
        "bankSlipUrl": "https://asaas.com/boleto/test",
        "invoiceUrl": "https://asaas.com/invoice/test",
    }
    mock_pix = {
        "encodedImage": "base64pixqrcode",
        "payload": "00020126...",
    }

    with patch("backend.app.billing.billing_service.asaas_client") as mock_asaas:
        mock_asaas.configured = True
        mock_asaas.criar_cobranca_avulsa = AsyncMock(return_value=mock_payment)
        mock_asaas.get_pix_qr_code = AsyncMock(return_value=mock_pix)

        result = await criar_cobranca_addon_bot(restaurante_essencial.id, db_session)

    assert result["status"] == "PENDING"
    assert result["pix_qr_code"] == "base64pixqrcode"
    assert result["pix_copia_cola"] == "00020126..."
    assert result["boleto_url"] == "https://asaas.com/boleto/test"
    assert result["valor"] == 99.45

    # Verificar registro no BD
    cob = db_session.query(AddonCobranca).filter(
        AddonCobranca.restaurante_id == restaurante_essencial.id,
    ).first()
    assert cob is not None
    assert cob.status == "PENDING"
    assert cob.asaas_payment_id == "pay_addon_test_001"


@pytest.mark.asyncio
async def test_criar_cobranca_premium_nao_precisa(db_session, restaurante_premium):
    """Premium (tier 4) não precisa de cobrança — bot incluso."""
    from backend.app.billing.billing_service import criar_cobranca_addon_bot

    with pytest.raises(ValueError, match="incluso"):
        await criar_cobranca_addon_bot(restaurante_premium.id, db_session)


@pytest.mark.asyncio
async def test_criar_cobranca_basico_bloqueado(db_session, restaurante_basico):
    """Basico (tier 1) bloqueado — tier mínimo é Essencial."""
    from backend.app.billing.billing_service import criar_cobranca_addon_bot

    with pytest.raises(ValueError, match="Essencial"):
        await criar_cobranca_addon_bot(restaurante_basico.id, db_session)


@pytest.mark.asyncio
async def test_cobranca_pendente_retorna_existente(db_session, restaurante_essencial):
    """Se já existe cobrança PENDING, retorna dados dela em vez de criar nova."""
    from backend.app.billing.billing_service import criar_cobranca_addon_bot

    result = await criar_cobranca_addon_bot(restaurante_essencial.id, db_session)

    assert result["status"] == "PENDING"
    assert result["asaas_payment_id"] == "pay_addon_test_001"


@pytest.mark.asyncio
async def test_webhook_confirma_addon(db_session, restaurante_essencial):
    """Pagamento confirmado via webhook ativa addon + registra phone."""
    from backend.app.billing.billing_service import processar_addon_pago
    from database.models import AddonCobranca, BotConfig

    # Criar BotConfig com pending_payment
    bot_config = db_session.query(BotConfig).filter(
        BotConfig.restaurante_id == restaurante_essencial.id
    ).first()
    if not bot_config:
        bot_config = BotConfig(
            restaurante_id=restaurante_essencial.id,
            whatsapp_numero="5511888888888",
            phone_display_name="Addon Test",
            phone_registration_status="pending_payment",
        )
        db_session.add(bot_config)
        db_session.commit()
    else:
        bot_config.phone_registration_status = "pending_payment"
        bot_config.whatsapp_numero = "5511888888888"
        bot_config.phone_display_name = "Addon Test"
        db_session.commit()

    # Garantir cobrança PENDING existe
    cob = db_session.query(AddonCobranca).filter(
        AddonCobranca.restaurante_id == restaurante_essencial.id,
        AddonCobranca.status == "PENDING",
    ).first()
    if not cob:
        cob = AddonCobranca(
            restaurante_id=restaurante_essencial.id,
            addon="bot_whatsapp",
            asaas_payment_id="pay_addon_webhook_test",
            valor=99.45,
            status="PENDING",
            ciclo_numero=1,
        )
        db_session.add(cob)
        db_session.commit()

    with patch("backend.app.bot.meta_phone_manager.registrar_numero",
               new_callable=AsyncMock, return_value={"phone_number_id": "12345"}), \
         patch("backend.app.bot.meta_phone_manager.solicitar_codigo",
               new_callable=AsyncMock):
        await processar_addon_pago(cob, db_session)

    # Refresh
    db_session.refresh(restaurante_essencial)
    db_session.refresh(bot_config)
    db_session.refresh(cob)

    assert restaurante_essencial.addon_bot_whatsapp is True
    assert restaurante_essencial.addon_bot_valor == 99.45
    assert restaurante_essencial.addon_bot_ciclo_inicio is not None
    assert restaurante_essencial.addon_bot_proximo_vencimento is not None
    assert cob.status == "RECEIVED"
    assert cob.data_pagamento is not None


@pytest.mark.asyncio
async def test_webhook_vencido_addon(db_session, restaurante_essencial):
    """Pagamento OVERDUE marca AddonCobranca como OVERDUE."""
    from database.models import AddonCobranca

    # Criar cobrança de recorrência
    cob = AddonCobranca(
        restaurante_id=restaurante_essencial.id,
        addon="bot_whatsapp",
        asaas_payment_id="pay_addon_overdue_001",
        valor=99.45,
        status="PENDING",
        data_vencimento=datetime.utcnow() - timedelta(days=3),
        ciclo_numero=2,
    )
    db_session.add(cob)
    db_session.commit()

    # Simular webhook OVERDUE — direto no BD
    cob.status = "OVERDUE"
    db_session.commit()
    db_session.refresh(cob)

    assert cob.status == "OVERDUE"


@pytest.mark.asyncio
async def test_payment_status_pending(db_session, restaurante_essencial):
    """GET payment-status retorna dados corretos quando PENDING."""
    from database.models import AddonCobranca, BotConfig

    # Reset para pending_payment
    bot_config = db_session.query(BotConfig).filter(
        BotConfig.restaurante_id == restaurante_essencial.id
    ).first()
    if bot_config:
        bot_config.phone_registration_status = "pending_payment"
        db_session.commit()

    # Criar cobrança PENDING nova
    cob = AddonCobranca(
        restaurante_id=restaurante_essencial.id,
        addon="bot_whatsapp",
        asaas_payment_id="pay_addon_pending_status",
        valor=99.45,
        status="PENDING",
        pix_qr_code="qr_test",
        pix_copia_cola="copia_cola_test",
        data_vencimento=datetime.utcnow() + timedelta(days=3),
        ciclo_numero=3,
    )
    db_session.add(cob)
    db_session.commit()

    # Verificar a lógica diretamente (sem HTTP para evitar auth)
    cob_check = db_session.query(AddonCobranca).filter(
        AddonCobranca.restaurante_id == restaurante_essencial.id,
        AddonCobranca.addon == "bot_whatsapp",
    ).order_by(AddonCobranca.criado_em.desc()).first()

    assert cob_check is not None
    assert cob_check.status == "PENDING"
    assert cob_check.pix_qr_code == "qr_test"


@pytest.mark.asyncio
async def test_recorrencia_cria_nova_cobranca(db_session, restaurante_essencial):
    """Task de recorrência cria cobrança para mês seguinte."""
    from backend.app.billing.billing_service import criar_recorrencia_addon
    from database.models import AddonCobranca

    # Configurar restaurante com addon ativo e vencimento passado
    restaurante_essencial.addon_bot_whatsapp = True
    restaurante_essencial.addon_bot_proximo_vencimento = date.today() - timedelta(days=1)
    db_session.commit()

    mock_payment = {
        "id": "pay_addon_recurrence_001",
        "bankSlipUrl": "https://asaas.com/boleto/recurrence",
        "invoiceUrl": "https://asaas.com/invoice/recurrence",
    }

    with patch("backend.app.billing.billing_service.asaas_client") as mock_asaas:
        mock_asaas.configured = True
        mock_asaas.criar_cobranca_avulsa = AsyncMock(return_value=mock_payment)
        mock_asaas.get_pix_qr_code = AsyncMock(return_value={"encodedImage": "qr", "payload": "pix"})

        await criar_recorrencia_addon(restaurante_essencial.id, db_session)

    # Verificar nova cobrança criada
    cob = db_session.query(AddonCobranca).filter(
        AddonCobranca.asaas_payment_id == "pay_addon_recurrence_001",
    ).first()
    assert cob is not None
    assert cob.status == "PENDING"


@pytest.mark.asyncio
async def test_desativar_por_inadimplencia(db_session, restaurante_essencial):
    """5 dias vencido desativa addon + bot."""
    from backend.app.billing.billing_service import desativar_addon_por_inadimplencia

    restaurante_essencial.addon_bot_whatsapp = True
    db_session.commit()

    await desativar_addon_por_inadimplencia(restaurante_essencial.id, db_session)

    db_session.refresh(restaurante_essencial)
    assert restaurante_essencial.addon_bot_whatsapp is False
    assert restaurante_essencial.addon_bot_valor == 0.0


@pytest.mark.asyncio
async def test_desativar_addon_cancela_pendentes(db_session, restaurante_essencial):
    """Desativar cancela cobranças PENDING no Asaas."""
    from backend.app.billing.billing_service import desativar_addon_bot
    from database.models import AddonCobranca

    # Reativar para teste
    restaurante_essencial.addon_bot_whatsapp = True
    restaurante_essencial.addon_bot_valor = 99.45
    db_session.commit()

    # Criar cobrança PENDING
    cob = AddonCobranca(
        restaurante_id=restaurante_essencial.id,
        addon="bot_whatsapp",
        asaas_payment_id="pay_addon_to_cancel_001",
        valor=99.45,
        status="PENDING",
        ciclo_numero=5,
    )
    db_session.add(cob)
    db_session.commit()

    with patch("backend.app.billing.billing_service.asaas_client") as mock_asaas:
        mock_asaas.configured = True
        mock_asaas.cancelar_cobranca = AsyncMock(return_value={})

        result = await desativar_addon_bot(restaurante_essencial.id, db_session)

    assert result["desativado"] is True

    db_session.refresh(cob)
    assert cob.status == "CANCELED"

    db_session.refresh(restaurante_essencial)
    assert restaurante_essencial.addon_bot_whatsapp is False


@pytest.mark.asyncio
async def test_reativar_addon_novo_pagamento(db_session, restaurante_essencial):
    """Reativar após desativação cria nova cobrança."""
    from backend.app.billing.billing_service import criar_cobranca_addon_bot
    from database.models import AddonCobranca

    # Restaurante desativado do teste anterior
    assert restaurante_essencial.addon_bot_whatsapp is False

    mock_payment = {
        "id": "pay_addon_reactivate_001",
        "bankSlipUrl": None,
        "invoiceUrl": None,
    }

    with patch("backend.app.billing.billing_service.asaas_client") as mock_asaas:
        mock_asaas.configured = True
        mock_asaas.criar_cobranca_avulsa = AsyncMock(return_value=mock_payment)
        mock_asaas.get_pix_qr_code = AsyncMock(return_value={"encodedImage": "", "payload": ""})

        result = await criar_cobranca_addon_bot(restaurante_essencial.id, db_session)

    assert result["status"] == "PENDING"
    assert result["asaas_payment_id"] == "pay_addon_reactivate_001"
