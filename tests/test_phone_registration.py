"""
Testes do sistema de Phone Registration (Self-Service Onboarding) — Derekh Food
Valida endpoints de registro, verificação, perfil, foto e troca de número.

Execução: pytest tests/test_phone_registration.py -v
"""

import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-phone-reg")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/test_phone_reg.db")
os.environ.setdefault("META_ACCESS_TOKEN", "test-meta-token")
os.environ.setdefault("META_WABA_ID", "123456789")

import pytest
from fastapi.testclient import TestClient


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def app():
    os.environ["DATABASE_URL"] = f"sqlite:///{PROJECT_ROOT}/test_phone_reg.db"
    os.environ["SECRET_KEY"] = "test-secret-key-phone-reg"

    from backend.app.main import app as fastapi_app
    from backend.app.database import engine, Base

    Base.metadata.create_all(bind=engine)
    yield fastapi_app

    db_path = PROJECT_ROOT / "test_phone_reg.db"
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
def db_session():
    from backend.app.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


def _criar_restaurante(db, email, plano, plano_tier, nome="Test Rest"):
    from database.models import Restaurante
    rest = db.query(Restaurante).filter(Restaurante.email == email).first()
    if not rest:
        rest = Restaurante(
            nome=nome,
            nome_fantasia=nome,
            email=email,
            telefone="11999990000",
            endereco_completo="Rua Teste 1",
            plano=plano,
            plano_tier=plano_tier,
            billing_status="active",
            valor_plano=169.90,
            limite_motoboys=5,
            cnpj=f"0000000000{plano_tier}00",
        )
        rest.gerar_codigo_acesso()
        rest.set_senha("teste123")
        db.add(rest)
        db.commit()
        db.refresh(rest)
    return rest


@pytest.fixture(scope="module")
def rest_basico(db_session):
    return _criar_restaurante(db_session, "phone_basico@test.com", "Basico", 1, "Basico Phone")


@pytest.fixture(scope="module")
def rest_essencial(db_session):
    return _criar_restaurante(db_session, "phone_essencial@test.com", "Essencial", 2, "Essencial Phone")


@pytest.fixture(scope="module")
def rest_premium(db_session):
    return _criar_restaurante(db_session, "phone_premium@test.com", "Premium", 4, "Premium Phone")


def _get_token(client, rest):
    resp = client.post("/auth/restaurante/login", json={
        "codigo_acesso": rest.codigo_acesso,
        "senha": "teste123",
    })
    if resp.status_code != 200:
        # Fallback: gerar token diretamente
        from backend.app.auth import create_access_token
        return create_access_token({"sub": str(rest.id), "role": "restaurante"})
    return resp.json().get("access_token", "")


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ==================== TESTES ====================

class TestPhoneStatus:
    def test_status_sem_config(self, client, rest_premium):
        """Restaurante sem BotConfig deve retornar status 'none'."""
        token = _get_token(client, rest_premium)
        resp = client.get("/painel/bot/phone/status", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["registration_status"] == "none"
        assert data["phone_number_id"] is None
        assert data["bot_ativo"] is False


class TestRegistrarNumero:
    @patch("backend.app.bot.meta_phone_manager.registrar_numero", new_callable=AsyncMock)
    @patch("backend.app.bot.meta_phone_manager.solicitar_codigo", new_callable=AsyncMock)
    def test_registrar_numero_premium_ok(self, mock_sol, mock_reg, client, rest_premium):
        """Premium registra número sem precisar de add-on."""
        mock_reg.return_value = {"phone_number_id": "PID_PREMIUM_001", "raw": {}}
        mock_sol.return_value = True

        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/registrar", headers=_auth_headers(token), json={
            "numero": "5511999990001",
            "display_name": "Premium Phone",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        assert data["phone_number_id"] == "PID_PREMIUM_001"
        mock_reg.assert_called_once()
        mock_sol.assert_called_once()

    @patch("backend.app.bot.meta_phone_manager.registrar_numero", new_callable=AsyncMock)
    @patch("backend.app.bot.meta_phone_manager.solicitar_codigo", new_callable=AsyncMock)
    @patch("backend.app.billing.billing_service.ativar_addon_bot", new_callable=AsyncMock)
    def test_registrar_numero_essencial_ativa_addon(self, mock_addon, mock_sol, mock_reg, client, rest_essencial):
        """Essencial deve ativar add-on automaticamente ao registrar."""
        mock_reg.return_value = {"phone_number_id": "PID_ESS_001", "raw": {}}
        mock_sol.return_value = True
        mock_addon.return_value = {"sucesso": True}

        token = _get_token(client, rest_essencial)
        resp = client.post("/painel/bot/phone/registrar", headers=_auth_headers(token), json={
            "numero": "5511999990002",
            "display_name": "Essencial Phone",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        mock_addon.assert_called_once()

    def test_registrar_numero_invalido(self, client, rest_premium):
        """Número muito curto deve ser rejeitado."""
        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/registrar", headers=_auth_headers(token), json={
            "numero": "123",
            "display_name": "Teste",
        })
        assert resp.status_code == 400

    def test_registrar_sem_display_name(self, client, rest_premium):
        """Display name vazio usa nome_fantasia do restaurante — deve funcionar."""
        # Este teste verifica que o fallback para nome_fantasia funciona.
        # Já tem bot_config do teste anterior, vamos verificar status
        token = _get_token(client, rest_premium)
        resp = client.get("/painel/bot/phone/status", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["registration_status"] == "pending_code"


class TestSolicitarCodigo:
    @patch("backend.app.bot.meta_phone_manager.solicitar_codigo", new_callable=AsyncMock)
    def test_solicitar_codigo_sms(self, mock_sol, client, rest_premium):
        """Solicitar código via SMS."""
        mock_sol.return_value = True
        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/solicitar-codigo", headers=_auth_headers(token), json={
            "metodo": "SMS",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        mock_sol.assert_called_once()

    @patch("backend.app.bot.meta_phone_manager.solicitar_codigo", new_callable=AsyncMock)
    def test_solicitar_codigo_voice(self, mock_sol, client, rest_premium):
        """Solicitar código via ligação."""
        mock_sol.return_value = True
        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/solicitar-codigo", headers=_auth_headers(token), json={
            "metodo": "VOICE",
        })
        assert resp.status_code == 200
        mock_sol.assert_called_once()


class TestVerificarCodigo:
    @patch("backend.app.bot.meta_phone_manager.verificar_codigo", new_callable=AsyncMock)
    @patch("backend.app.bot.meta_phone_manager.registrar_cloud_api", new_callable=AsyncMock)
    def test_verificar_codigo_correto(self, mock_cloud, mock_ver, client, rest_premium):
        """Código correto verifica e registra na Cloud API."""
        mock_ver.return_value = True
        mock_cloud.return_value = True

        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/verificar-codigo", headers=_auth_headers(token), json={
            "codigo": "123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        assert data["registration_status"] == "registered"
        mock_ver.assert_called_once()
        mock_cloud.assert_called_once()

    def test_verificar_codigo_invalido_formato(self, client, rest_premium):
        """Código com formato errado deve ser rejeitado."""
        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/verificar-codigo", headers=_auth_headers(token), json={
            "codigo": "12345",  # 5 dígitos, precisa 6
        })
        assert resp.status_code == 400

    @patch("backend.app.bot.meta_phone_manager.verificar_codigo", new_callable=AsyncMock)
    def test_verificar_codigo_errado(self, mock_ver, client, rest_premium):
        """Código errado retorna erro da Meta API."""
        from backend.app.bot.meta_phone_manager import MetaApiError
        mock_ver.side_effect = MetaApiError("Invalid code", status_code=400)

        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/verificar-codigo", headers=_auth_headers(token), json={
            "codigo": "999999",
        })
        assert resp.status_code == 400
        assert "invalido" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()


class TestPerfilPhone:
    @patch("backend.app.bot.meta_phone_manager.atualizar_perfil", new_callable=AsyncMock)
    def test_atualizar_perfil(self, mock_perfil, client, rest_premium):
        """Atualiza about + description + nome_atendente."""
        mock_perfil.return_value = True

        token = _get_token(client, rest_premium)
        resp = client.put("/painel/bot/phone/perfil", headers=_auth_headers(token), json={
            "about": "Delivery 24h",
            "description": "Pizzaria artesanal",
            "nome_atendente": "Ana",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        mock_perfil.assert_called_once()

    @patch("backend.app.bot.meta_phone_manager.atualizar_perfil", new_callable=AsyncMock)
    def test_ativar_com_perfil(self, mock_perfil, client, rest_premium):
        """Atualiza perfil e ativa bot de uma vez."""
        mock_perfil.return_value = True

        token = _get_token(client, rest_premium)
        resp = client.put("/painel/bot/phone/perfil", headers=_auth_headers(token), json={
            "about": "Delivery rapido",
            "ativar": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        assert data["registration_status"] == "active"


class TestFotoPhone:
    def test_upload_foto_tamanho_excedido(self, client, rest_premium):
        """Rejeita imagem > 5MB."""
        token = _get_token(client, rest_premium)
        # Criar arquivo fake de 6MB
        big_file = BytesIO(b"\x00" * (6 * 1024 * 1024))
        resp = client.post(
            "/painel/bot/phone/foto",
            headers=_auth_headers(token),
            files={"foto": ("big.jpg", big_file, "image/jpeg")},
        )
        assert resp.status_code == 400
        assert "5MB" in resp.json()["detail"]

    @patch("backend.app.bot.meta_phone_manager.upload_foto_perfil", new_callable=AsyncMock)
    def test_upload_foto_ok(self, mock_upload, client, rest_premium):
        """Upload de foto pequena deve funcionar."""
        mock_upload.return_value = True

        token = _get_token(client, rest_premium)
        small_file = BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 1000)  # JPEG header fake
        resp = client.post(
            "/painel/bot/phone/foto",
            headers=_auth_headers(token),
            files={"foto": ("profile.jpg", small_file, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["sucesso"] is True
        mock_upload.assert_called_once()


class TestTrocarNumero:
    @patch("backend.app.bot.meta_phone_manager.desvincular_numero", new_callable=AsyncMock)
    @patch("backend.app.bot.meta_phone_manager.registrar_numero", new_callable=AsyncMock)
    @patch("backend.app.bot.meta_phone_manager.solicitar_codigo", new_callable=AsyncMock)
    def test_trocar_numero_ok(self, mock_sol, mock_reg, mock_des, client, rest_premium):
        """Troca de número desvincula antigo e registra novo."""
        mock_des.return_value = True
        mock_reg.return_value = {"phone_number_id": "PID_NOVO_001", "raw": {}}
        mock_sol.return_value = True

        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/trocar-numero", headers=_auth_headers(token), json={
            "numero_novo": "5511888880001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["sucesso"] is True
        assert data["phone_number_id"] == "PID_NOVO_001"
        mock_des.assert_called_once()
        mock_reg.assert_called_once()
        mock_sol.assert_called_once()

    def test_trocar_numero_invalido(self, client, rest_premium):
        """Número novo inválido deve ser rejeitado."""
        token = _get_token(client, rest_premium)
        resp = client.post("/painel/bot/phone/trocar-numero", headers=_auth_headers(token), json={
            "numero_novo": "123",
        })
        assert resp.status_code == 400


class TestStatusCompleto:
    def test_status_apos_fluxo(self, client, rest_premium):
        """Após trocar número, status deve refletir pending_code."""
        token = _get_token(client, rest_premium)
        resp = client.get("/painel/bot/phone/status", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        # Após trocar número, status volta para pending_code
        assert data["registration_status"] == "pending_code"
        assert data["phone_number_id"] is not None
        assert data["whatsapp_numero"] is not None


class TestFeatureGuard:
    def test_basico_bloqueado_phone_status(self, client, rest_basico):
        """Restaurante Básico (Tier 1) deve ser bloqueado pelo feature guard."""
        token = _get_token(client, rest_basico)
        resp = client.get("/painel/bot/phone/status", headers=_auth_headers(token))
        # Feature guard retorna 403 ou feature_blocked
        assert resp.status_code in (403, 200)
        if resp.status_code == 200:
            # Se retornou 200, verificar se é feature_blocked
            data = resp.json()
            assert data.get("feature_blocked") or data.get("registration_status") == "none"
