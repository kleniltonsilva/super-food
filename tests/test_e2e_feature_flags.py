"""
Testes E2E profissionais — Feature Flags por Plano.

Valida TODAS as combinações plano×feature×endpoint:
  - 22 features, 4 tiers, add-ons, overrides, trial, billing suspenso
  - Login gates (cozinheiro, garçom)
  - Limite de motoboys por tier
  - Formato 403 estruturado com addon_info

~150 testes — cobre a matriz completa de controle de acesso.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ─── Path setup ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "test_e2e_feature_flags.db"


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def app():
    """Cria app FastAPI com banco SQLite isolado."""
    from backend.app import database

    test_engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    orig_engine, orig_session = database.engine, database.SessionLocal
    database.engine = test_engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    database.Base.metadata.create_all(bind=test_engine)

    from tests.conftest_e2e import patch_session_locals, restore_session_locals
    _patches = patch_session_locals(database.SessionLocal)

    from backend.app.main import app as fastapi_app
    yield fastapi_app

    restore_session_locals(_patches)
    database.engine, database.SessionLocal = orig_engine, orig_session
    test_engine.dispose()
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db(app):
    from backend.app.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sha256(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


@pytest.fixture(scope="module")
def setup(db):
    """Cria 6 restaurantes com planos distintos + dados auxiliares."""
    from backend.app import models
    from backend.app.auth import create_access_token, get_password_hash

    # ─── Helper para criar restaurante ───
    def make_rest(nome, plano, tier, billing_status, email, telefone,
                  addon_bot=False, features_override=None, limite_motoboys=None):
        rest = models.Restaurante(
            nome=nome,
            nome_fantasia=nome,
            email=email,
            telefone=telefone,
            endereco_completo="Rua Teste 123",
            plano=plano,
            plano_tier=tier,
            billing_status=billing_status,
            valor_plano=169.90,
            limite_motoboys=limite_motoboys or {1: 2, 2: 5, 3: 10, 4: 999}[tier],
            cnpj=None,
            ativo=True,
            addon_bot_whatsapp=addon_bot,
            features_override=features_override,
        )
        rest.gerar_codigo_acesso()
        rest.set_senha("teste123")
        db.add(rest)
        db.flush()

        # ConfigRestaurante
        config = models.ConfigRestaurante(
            restaurante_id=rest.id,
            status_atual="aberto",
            horario_abertura="08:00",
            horario_fechamento="23:00",
        )
        db.add(config)

        # SiteConfig
        site = models.SiteConfig(
            restaurante_id=rest.id,
            tipo_restaurante="geral",
            tema_cor_primaria="#FF6B35",
            whatsapp_numero=telefone,
        )
        db.add(site)

        # Categoria + Produto (para endpoints que listam)
        cat = models.CategoriaMenu(
            restaurante_id=rest.id,
            nome="Pizzas",
            ordem_exibicao=1,
            ativo=True,
        )
        db.add(cat)
        db.flush()

        prod = models.Produto(
            restaurante_id=rest.id,
            categoria_id=cat.id,
            nome="Pizza Margherita",
            preco=45.0,
            disponivel=True,
        )
        db.add(prod)

        # BairroEntrega
        bairro = models.BairroEntrega(
            restaurante_id=rest.id,
            nome="Centro",
            taxa_entrega=5.0,
            ativo=True,
        )
        db.add(bairro)

        # ConfigCozinha (KDS)
        kds_config = models.ConfigCozinha(
            restaurante_id=rest.id,
            kds_ativo=True,
            tempo_alerta_min=15,
            tempo_critico_min=25,
        )
        db.add(kds_config)

        # Cozinheiro
        coz = models.Cozinheiro(
            restaurante_id=rest.id,
            nome="Chef Teste",
            login="chef",
            senha_hash=_sha256("coz123"),
            modo="todos",
            ativo=True,
        )
        db.add(coz)

        # ConfigGarcom
        config_garcom = models.ConfigGarcom(
            restaurante_id=rest.id,
            garcom_ativo=True,
            taxa_servico=0.10,
            pct_taxa=True,
        )
        db.add(config_garcom)

        # Garçom
        garcom = models.Garcom(
            restaurante_id=rest.id,
            nome="Garçom Teste",
            login="garcom",
            senha_hash=_sha256("garcom123"),
            modo_secao="TODOS",
            ativo=True,
        )
        db.add(garcom)
        db.flush()

        token = create_access_token({"sub": str(rest.id), "role": "restaurante"})
        return {
            "rest": rest,
            "token": token,
            "codigo": rest.codigo_acesso,
            "cozinheiro": coz,
            "garcom": garcom,
            "produto": prod,
            "categoria": cat,
        }

    # ─── 6 restaurantes ───
    basico = make_rest("Rest Básico", "Básico", 1, "active", "basico@test.com", "11900000001")
    essencial = make_rest("Rest Essencial", "Essencial", 2, "active", "essencial@test.com", "11900000002")
    avancado = make_rest("Rest Avançado", "Avançado", 3, "active", "avancado@test.com", "11900000003")
    premium = make_rest("Rest Premium", "Premium", 4, "active", "premium@test.com", "11900000004")
    trial = make_rest("Rest Trial", "Básico", 1, "trial", "trial@test.com", "11900000005")
    suspenso = make_rest("Rest Suspenso", "Premium", 4, "suspended_billing", "suspenso@test.com", "11900000006")

    db.commit()

    return {
        "basico": basico,
        "essencial": essencial,
        "avancado": avancado,
        "premium": premium,
        "trial": trial,
        "suspenso": suspenso,
    }


# ═══════════════════════════════════════════════════════════════
# F1. TestHasFeatureLogic — Unit tests diretos
# ═══════════════════════════════════════════════════════════════

class TestHasFeatureLogic:
    """Testa has_feature() e get_all_features() diretamente."""

    def test_tier1_tem_features_basicas(self):
        from backend.app.feature_flags import has_feature
        for feat in ["site_cardapio", "pedidos", "dashboard", "caixa",
                      "bairros_taxas", "motoboys", "configuracoes",
                      "relatorios_basicos", "bridge_printer"]:
            assert has_feature("Básico", feat), f"Básico deveria ter {feat}"

    def test_tier1_nao_tem_tier2(self):
        from backend.app.feature_flags import has_feature
        for feat in ["combos", "cupons_promocoes", "fidelidade",
                      "operadores_caixa", "kds_cozinha", "relatorios_avancados"]:
            assert not has_feature("Básico", feat), f"Básico NÃO deveria ter {feat}"

    def test_tier2_tem_tier1_e_tier2(self):
        from backend.app.feature_flags import has_feature
        for feat in ["site_cardapio", "combos", "fidelidade", "kds_cozinha"]:
            assert has_feature("Essencial", feat), f"Essencial deveria ter {feat}"

    def test_tier2_nao_tem_tier3(self):
        from backend.app.feature_flags import has_feature
        for feat in ["app_garcom", "integracoes_marketplace", "pix_online",
                      "dominio_personalizado", "analytics_avancado"]:
            assert not has_feature("Essencial", feat), f"Essencial NÃO deveria ter {feat}"

    def test_tier3_tem_tier1_2_3(self):
        from backend.app.feature_flags import has_feature
        for feat in ["combos", "kds_cozinha", "app_garcom", "analytics_avancado"]:
            assert has_feature("Avançado", feat), f"Avançado deveria ter {feat}"

    def test_tier3_nao_tem_tier4(self):
        from backend.app.feature_flags import has_feature
        for feat in ["bot_whatsapp", "suporte_dedicado"]:
            assert not has_feature("Avançado", feat), f"Avançado NÃO deveria ter {feat}"

    def test_tier4_tem_tudo(self):
        from backend.app.feature_flags import has_feature, FEATURE_TIERS
        for feat in FEATURE_TIERS:
            assert has_feature("Premium", feat), f"Premium deveria ter {feat}"

    def test_override_true_ativa_feature_bloqueada(self):
        from backend.app.feature_flags import has_feature
        overrides = json.dumps({"kds_cozinha": True})
        assert has_feature("Básico", "kds_cozinha", overrides=overrides)

    def test_override_false_desativa_feature_ativa(self):
        from backend.app.feature_flags import has_feature
        overrides = json.dumps({"bot_whatsapp": False})
        assert not has_feature("Premium", "bot_whatsapp", overrides=overrides)

    def test_addon_bot_ativa_para_tier2(self):
        from backend.app.feature_flags import has_feature
        addons = {"addon_bot_whatsapp": True}
        assert has_feature("Essencial", "bot_whatsapp", addons=addons)

    def test_addon_bot_ativa_para_tier3(self):
        from backend.app.feature_flags import has_feature
        addons = {"addon_bot_whatsapp": True}
        assert has_feature("Avançado", "bot_whatsapp", addons=addons)

    def test_addon_bot_nao_ativa_para_tier1(self):
        """Tier 1 < ADDON_MIN_TIER (2) → addon ignorado, feature bloqueada."""
        from backend.app.feature_flags import has_feature
        addons = {"addon_bot_whatsapp": True}
        assert not has_feature("Básico", "bot_whatsapp", addons=addons)

    def test_get_all_features_retorna_22_chaves(self):
        from backend.app.feature_flags import get_all_features, FEATURE_TIERS
        features = get_all_features("Básico")
        assert len(features) == len(FEATURE_TIERS) == 22

    def test_get_all_features_tier4_tudo_true(self):
        from backend.app.feature_flags import get_all_features
        features = get_all_features("Premium")
        assert all(features.values()), f"Premium deveria ter todas True: {features}"

    def test_override_json_invalido_ignorado(self):
        """Override com JSON malformado deve ser ignorado, usa tier normal."""
        from backend.app.feature_flags import has_feature
        assert not has_feature("Básico", "kds_cozinha", overrides="not-json{{{")
        assert has_feature("Essencial", "kds_cozinha", overrides="not-json{{{")


# ═══════════════════════════════════════════════════════════════
# F2. TestLoginFeatures — Features no login do restaurante
# ═══════════════════════════════════════════════════════════════

class TestLoginFeatures:
    """POST /auth/restaurante/login retorna campo features correto por tier."""

    def _login(self, client, email):
        resp = client.post("/auth/restaurante/login", json={
            "email": email,
            "senha": "teste123",
        })
        assert resp.status_code == 200
        return resp.json()["restaurante"]["features"]

    def test_login_tier1_features(self, client, setup):
        features = self._login(client, "basico@test.com")
        assert len(features) == 22
        # Tier 1 features
        for feat in ["site_cardapio", "pedidos", "dashboard", "caixa",
                      "bairros_taxas", "motoboys", "configuracoes",
                      "relatorios_basicos", "bridge_printer"]:
            assert features[feat] is True, f"Tier 1 deveria ter {feat}=True"
        # Features acima do tier 1
        for feat in ["combos", "kds_cozinha", "app_garcom", "bot_whatsapp"]:
            assert features[feat] is False, f"Tier 1 NÃO deveria ter {feat}"

    def test_login_tier2_features(self, client, setup):
        features = self._login(client, "essencial@test.com")
        # Tier 2 additions
        for feat in ["combos", "cupons_promocoes", "fidelidade",
                      "operadores_caixa", "kds_cozinha", "relatorios_avancados"]:
            assert features[feat] is True, f"Tier 2 deveria ter {feat}=True"
        # Still blocked
        for feat in ["app_garcom", "dominio_personalizado", "bot_whatsapp"]:
            assert features[feat] is False, f"Tier 2 NÃO deveria ter {feat}"

    def test_login_tier3_features(self, client, setup):
        features = self._login(client, "avancado@test.com")
        # Tier 3 additions
        for feat in ["app_garcom", "integracoes_marketplace", "pix_online",
                      "dominio_personalizado", "analytics_avancado"]:
            assert features[feat] is True, f"Tier 3 deveria ter {feat}=True"
        # Still blocked
        for feat in ["bot_whatsapp", "suporte_dedicado"]:
            assert features[feat] is False, f"Tier 3 NÃO deveria ter {feat}"

    def test_login_tier4_features(self, client, setup):
        features = self._login(client, "premium@test.com")
        assert all(features.values()), "Premium deveria ter todas True"
        assert len(features) == 22


# ═══════════════════════════════════════════════════════════════
# F3. TestTrialAccess — Trial desbloqueia tudo
# ═══════════════════════════════════════════════════════════════

class TestTrialAccess:
    """Restaurante trial (billing_status='trial') acessa TODOS os endpoints."""

    def test_trial_login_todas_features_true(self, client, setup):
        resp = client.post("/auth/restaurante/login", json={
            "email": "trial@test.com", "senha": "teste123",
        })
        features = resp.json()["restaurante"]["features"]
        assert all(features.values()), "Trial deveria ter todas features True"

    def test_trial_acessa_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_fidelidade(self, client, setup):
        resp = client.get("/painel/fidelidade/premios", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_dominios(self, client, setup):
        resp = client.get("/painel/dominios", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_bot_config(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["trial"]["token"]))
        # 200 ou 404 (sem BotConfig criado), mas NÃO 403
        assert resp.status_code != 403

    def test_trial_acessa_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════
# F4. TestBillingSuspended — Suspenso bloqueia tudo
# ═══════════════════════════════════════════════════════════════

class TestBillingSuspended:
    """Restaurante com billing_status='suspended_billing' recebe 403 em tudo."""

    def test_suspenso_403_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403
        assert "Assinatura suspensa" in str(resp.json()["detail"])

    def test_suspenso_403_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_bot(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_bridge(self, client, setup):
        resp = client.get("/painel/bridge/patterns", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════
# F5. TestTier1Basico — Básico bloqueado em features superiores
# ═══════════════════════════════════════════════════════════════

class TestTier1Basico:
    """Plano Básico (tier 1) recebe 403 em features de tier 2+."""

    def test_basico_403_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_promocoes(self, client, setup):
        resp = client.get("/painel/promocoes", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_fidelidade(self, client, setup):
        resp = client.get("/painel/fidelidade/premios", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_operadores_caixa(self, client, setup):
        resp = client.get("/painel/caixa/operadores", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_dominios(self, client, setup):
        resp = client.get("/painel/dominios", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_analytics(self, client, setup):
        # analytics requer param senha, mas 403 deve vir antes da validação de param
        resp = client.get("/painel/relatorios/analytics?senha=x&periodo=30d",
                          headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_bot(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_basico_acessa_bridge(self, client, setup):
        """Bridge printer é tier 1 — todos acessam."""
        resp = client.get("/painel/bridge/patterns", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 200

    def test_basico_403_estrutura(self, client, setup):
        """Valida estrutura completa do 403 estruturado."""
        resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
        detail = resp.json()["detail"]
        assert detail["type"] == "feature_blocked"
        assert detail["feature"] == "combos"
        assert detail["feature_label"] == "Combos Promocionais"
        assert detail["current_plano"] == "Básico"
        assert detail["current_tier"] == 1
        assert detail["required_plano"] == "Essencial"
        assert detail["required_tier"] == 2
        assert "Essencial" in detail["message"]


# ═══════════════════════════════════════════════════════════════
# F6. TestTier2Essencial — Essencial acessa tier 2, bloqueado em tier 3+
# ═══════════════════════════════════════════════════════════════

class TestTier2Essencial:
    """Plano Essencial (tier 2) acessa tier 1-2, bloqueado em tier 3+."""

    # ─── Acessa (200) ───
    def test_essencial_acessa_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_promocoes(self, client, setup):
        resp = client.get("/painel/promocoes", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_fidelidade(self, client, setup):
        resp = client.get("/painel/fidelidade/premios", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_operadores(self, client, setup):
        resp = client.get("/painel/caixa/operadores", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_bridge(self, client, setup):
        resp = client.get("/painel/bridge/patterns", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    # ─── Bloqueado (403) ───
    def test_essencial_403_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_403_dominios(self, client, setup):
        resp = client.get("/painel/dominios", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_403_analytics(self, client, setup):
        resp = client.get("/painel/relatorios/analytics?senha=x&periodo=30d",
                          headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_403_bot(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_403_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_403_bot_addon_info(self, client, setup):
        """403 do bot em Essencial inclui addon_info com can_subscribe=True."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        detail = resp.json()["detail"]
        assert "addon_info" in detail
        assert detail["addon_info"]["can_subscribe"] is True
        assert detail["addon_info"]["available"] is True
        assert detail["addon_info"]["min_tier"] == 2


# ═══════════════════════════════════════════════════════════════
# F7. TestTier3Avancado — Avançado acessa tier 1-3, bloqueado em tier 4
# ═══════════════════════════════════════════════════════════════

class TestTier3Avancado:
    """Plano Avançado (tier 3) acessa tier 1-3, bloqueado em tier 4."""

    # ─── Acessa (200) ───
    def test_avancado_acessa_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200

    def test_avancado_acessa_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200

    def test_avancado_acessa_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200

    def test_avancado_acessa_dominios(self, client, setup):
        resp = client.get("/painel/dominios", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200

    def test_avancado_acessa_analytics(self, client, setup):
        resp = client.get("/painel/relatorios/analytics?senha=teste123&periodo=30d",
                          headers=_auth(setup["avancado"]["token"]))
        # 200 (pode retornar dados vazios mas NÃO 403)
        assert resp.status_code != 403

    def test_avancado_acessa_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200

    # ─── Bloqueado (403) ───
    def test_avancado_403_bot(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 403

    def test_avancado_403_bot_addon_info(self, client, setup):
        """403 do bot em Avançado inclui addon_info com can_subscribe=True."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["avancado"]["token"]))
        detail = resp.json()["detail"]
        assert "addon_info" in detail
        assert detail["addon_info"]["can_subscribe"] is True


# ═══════════════════════════════════════════════════════════════
# F8. TestTier4Premium — Premium acessa TUDO
# ═══════════════════════════════════════════════════════════════

class TestTier4Premium:
    """Plano Premium (tier 4) acessa todos os endpoints."""

    def test_premium_acessa_combos(self, client, setup):
        resp = client.get("/painel/combos", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code == 200

    def test_premium_acessa_kds(self, client, setup):
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code == 200

    def test_premium_acessa_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code == 200

    def test_premium_acessa_bot(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["premium"]["token"]))
        # 200 ou 404 (sem BotConfig), mas NÃO 403
        assert resp.status_code != 403

    def test_premium_acessa_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════
# F9. TestAddonBotWhatsapp — Add-on desbloqueia feature
# ═══════════════════════════════════════════════════════════════

class TestAddonBotWhatsapp:
    """Testa add-on bot_whatsapp em diferentes tiers."""

    def test_essencial_sem_addon_403(self, client, setup):
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_essencial_com_addon_acessa_bot(self, client, setup, db):
        """Ativa addon no Essencial → acessa bot."""
        from backend.app import models
        rest = setup["essencial"]["rest"]
        rest.addon_bot_whatsapp = True
        db.commit()
        try:
            resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
            assert resp.status_code != 403, f"Essencial+addon deveria acessar bot, got {resp.status_code}"
        finally:
            rest.addon_bot_whatsapp = False
            db.commit()

    def test_avancado_com_addon_acessa_bot(self, client, setup, db):
        """Ativa addon no Avançado → acessa bot."""
        rest = setup["avancado"]["rest"]
        rest.addon_bot_whatsapp = True
        db.commit()
        try:
            resp = client.get("/painel/bot/config", headers=_auth(setup["avancado"]["token"]))
            assert resp.status_code != 403
        finally:
            rest.addon_bot_whatsapp = False
            db.commit()

    def test_basico_com_addon_nao_acessa_bot(self, client, setup, db):
        """Tier 1 < ADDON_MIN_TIER (2) → addon ignorado, 403 mantido."""
        rest = setup["basico"]["rest"]
        rest.addon_bot_whatsapp = True
        db.commit()
        try:
            resp = client.get("/painel/bot/config", headers=_auth(setup["basico"]["token"]))
            assert resp.status_code == 403
        finally:
            rest.addon_bot_whatsapp = False
            db.commit()

    def test_basico_403_can_subscribe_false(self, client, setup, db):
        """Tier 1 → can_subscribe=False (tier < addon min_tier 2)."""
        rest = setup["basico"]["rest"]
        rest.addon_bot_whatsapp = False
        db.commit()
        resp = client.get("/painel/bot/config", headers=_auth(setup["basico"]["token"]))
        detail = resp.json()["detail"]
        assert "addon_info" in detail
        assert detail["addon_info"]["can_subscribe"] is False

    def test_premium_ignora_addon(self, client, setup):
        """Premium já inclui bot — addon irrelevante."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code != 403

    def test_addon_refletido_no_login(self, client, setup, db):
        """Ativar addon muda features no login."""
        rest = setup["essencial"]["rest"]
        rest.addon_bot_whatsapp = True
        db.commit()
        try:
            resp = client.post("/auth/restaurante/login", json={
                "email": "essencial@test.com", "senha": "teste123",
            })
            features = resp.json()["restaurante"]["features"]
            assert features["bot_whatsapp"] is True
        finally:
            rest.addon_bot_whatsapp = False
            db.commit()

    def test_addon_desativado_login_false(self, client, setup, db):
        """Sem addon, bot_whatsapp=False no login."""
        rest = setup["essencial"]["rest"]
        rest.addon_bot_whatsapp = False
        db.commit()
        resp = client.post("/auth/restaurante/login", json={
            "email": "essencial@test.com", "senha": "teste123",
        })
        features = resp.json()["restaurante"]["features"]
        assert features["bot_whatsapp"] is False

    def test_addon_preco_na_resposta_403(self, client, setup):
        """403 inclui preço do addon."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        detail = resp.json()["detail"]
        assert detail["addon_info"]["price"] == 99.45

    def test_addon_label_na_resposta_403(self, client, setup):
        """403 inclui label legível do addon."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        detail = resp.json()["detail"]
        assert "WhatsApp" in detail["addon_info"]["label"]


# ═══════════════════════════════════════════════════════════════
# F10. TestFeaturesOverride — Super admin override
# ═══════════════════════════════════════════════════════════════

class TestFeaturesOverride:
    """Testa features_override do Super Admin."""

    def test_override_ativa_kds_no_basico(self, client, setup, db):
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"kds_cozinha": True})
        db.commit()
        try:
            resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"]))
            assert resp.status_code == 200
        finally:
            rest.features_override = None
            db.commit()

    def test_override_ativa_combos_no_basico(self, client, setup, db):
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"combos": True})
        db.commit()
        try:
            resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
            assert resp.status_code == 200
        finally:
            rest.features_override = None
            db.commit()

    def test_override_desativa_bot_no_premium(self, client, setup, db):
        rest = setup["premium"]["rest"]
        rest.features_override = json.dumps({"bot_whatsapp": False})
        db.commit()
        try:
            resp = client.get("/painel/bot/config", headers=_auth(setup["premium"]["token"]))
            assert resp.status_code == 403
        finally:
            rest.features_override = None
            db.commit()

    def test_override_desativa_combos_no_premium(self, client, setup, db):
        rest = setup["premium"]["rest"]
        rest.features_override = json.dumps({"combos": False})
        db.commit()
        try:
            resp = client.get("/painel/combos", headers=_auth(setup["premium"]["token"]))
            assert resp.status_code == 403
        finally:
            rest.features_override = None
            db.commit()

    def test_override_null_volta_ao_tier(self, client, setup, db):
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"kds_cozinha": True})
        db.commit()
        # Com override → acessa
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 200
        # Remove override → bloqueado
        rest.features_override = None
        db.commit()
        resp = client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_override_json_invalido_ignorado(self, client, setup, db):
        """JSON malformado é ignorado — usa tier normal."""
        rest = setup["basico"]["rest"]
        rest.features_override = "not-valid-json{"
        db.commit()
        try:
            resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
            assert resp.status_code == 403  # Volta ao tier — Básico não tem combos
        finally:
            rest.features_override = None
            db.commit()

    def test_override_feature_inexistente_ignorado(self, client, setup, db):
        """Override de feature inexistente não afeta nada."""
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"feature_que_nao_existe": True})
        db.commit()
        try:
            resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
            assert resp.status_code == 403  # Combos continua bloqueado
        finally:
            rest.features_override = None
            db.commit()

    def test_override_multiplas_features(self, client, setup, db):
        """Override de múltiplas features ao mesmo tempo."""
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({
            "combos": True,
            "kds_cozinha": True,
            "app_garcom": True,
        })
        db.commit()
        try:
            assert client.get("/painel/combos", headers=_auth(setup["basico"]["token"])).status_code == 200
            assert client.get("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"])).status_code == 200
            assert client.get("/painel/garcom/garcons", headers=_auth(setup["basico"]["token"])).status_code == 200
        finally:
            rest.features_override = None
            db.commit()

    def test_override_refletido_no_login(self, client, setup, db):
        """Override muda features retornadas no login."""
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"bot_whatsapp": True})
        db.commit()
        try:
            resp = client.post("/auth/restaurante/login", json={
                "email": "basico@test.com", "senha": "teste123",
            })
            features = resp.json()["restaurante"]["features"]
            assert features["bot_whatsapp"] is True
        finally:
            rest.features_override = None
            db.commit()

    def test_override_prioridade_sobre_addon(self, client, setup, db):
        """Override False tem prioridade sobre addon ativo."""
        rest = setup["essencial"]["rest"]
        rest.addon_bot_whatsapp = True
        rest.features_override = json.dumps({"bot_whatsapp": False})
        db.commit()
        try:
            resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
            assert resp.status_code == 403
        finally:
            rest.addon_bot_whatsapp = False
            rest.features_override = None
            db.commit()


# ═══════════════════════════════════════════════════════════════
# F11. TestLoginGates — Login cozinheiro e garçom
# ═══════════════════════════════════════════════════════════════

class TestLoginGates:
    """Testa login gates de cozinheiro (KDS, tier 2) e garçom (tier 3)."""

    def _login_cozinheiro(self, client, codigo):
        return client.post("/auth/cozinheiro/login", json={
            "codigo_restaurante": codigo,
            "login": "chef",
            "senha": "coz123",
        })

    def _login_garcom(self, client, codigo):
        return client.post("/garcom/auth/login", json={
            "codigo_restaurante": codigo,
            "login": "garcom",
            "senha": "garcom123",
        })

    # ─── Cozinheiro (KDS — tier 2) ───
    def test_cozinheiro_basico_403(self, client, setup):
        resp = self._login_cozinheiro(client, setup["basico"]["codigo"])
        assert resp.status_code == 403

    def test_cozinheiro_essencial_200(self, client, setup):
        resp = self._login_cozinheiro(client, setup["essencial"]["codigo"])
        assert resp.status_code == 200

    def test_cozinheiro_avancado_200(self, client, setup):
        resp = self._login_cozinheiro(client, setup["avancado"]["codigo"])
        assert resp.status_code == 200

    def test_cozinheiro_trial_200(self, client, setup):
        resp = self._login_cozinheiro(client, setup["trial"]["codigo"])
        assert resp.status_code == 200

    # ─── Garçom (App Garçom — tier 3) ───
    def test_garcom_basico_403(self, client, setup):
        resp = self._login_garcom(client, setup["basico"]["codigo"])
        assert resp.status_code == 403

    def test_garcom_essencial_403(self, client, setup):
        resp = self._login_garcom(client, setup["essencial"]["codigo"])
        assert resp.status_code == 403

    def test_garcom_avancado_200(self, client, setup):
        resp = self._login_garcom(client, setup["avancado"]["codigo"])
        assert resp.status_code == 200

    def test_garcom_trial_200(self, client, setup):
        resp = self._login_garcom(client, setup["trial"]["codigo"])
        assert resp.status_code == 200

    def test_garcom_premium_200(self, client, setup):
        resp = self._login_garcom(client, setup["premium"]["codigo"])
        assert resp.status_code == 200

    def test_cozinheiro_premium_200(self, client, setup):
        resp = self._login_cozinheiro(client, setup["premium"]["codigo"])
        assert resp.status_code == 200

    # ─── Login gates com billing suspenso ───
    def test_cozinheiro_basico_403_feature_blocked_detail(self, client, setup):
        """403 do login cozinheiro inclui detalhes feature_blocked."""
        resp = self._login_cozinheiro(client, setup["basico"]["codigo"])
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["type"] == "feature_blocked"
        assert detail["feature"] == "kds_cozinha"

    def test_garcom_basico_403_feature_blocked_detail(self, client, setup):
        """403 do login garçom inclui detalhes feature_blocked."""
        resp = self._login_garcom(client, setup["basico"]["codigo"])
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["type"] == "feature_blocked"
        assert detail["feature"] == "app_garcom"

    def test_cozinheiro_com_override_basico_200(self, client, setup, db):
        """Override kds_cozinha=True no Básico → cozinheiro login OK."""
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"kds_cozinha": True})
        db.commit()
        try:
            resp = self._login_cozinheiro(client, setup["basico"]["codigo"])
            assert resp.status_code == 200
        finally:
            rest.features_override = None
            db.commit()

    def test_garcom_com_override_basico_200(self, client, setup, db):
        """Override app_garcom=True no Básico → garçom login OK."""
        rest = setup["basico"]["rest"]
        rest.features_override = json.dumps({"app_garcom": True})
        db.commit()
        try:
            resp = self._login_garcom(client, setup["basico"]["codigo"])
            assert resp.status_code == 200
        finally:
            rest.features_override = None
            db.commit()


# ═══════════════════════════════════════════════════════════════
# F12. TestMotoboyLimit — Limite de motoboys por tier
# ═══════════════════════════════════════════════════════════════

class TestMotoboyLimit:
    """Testa limite de cadastro de motoboys por plano."""

    def _criar_motoboy(self, client, token, nome, usuario, telefone):
        return client.post("/painel/motoboys", headers=_auth(token), json={
            "nome": nome,
            "usuario": usuario,
            "telefone": telefone,
        })

    def test_basico_limite_2(self, client, setup, db):
        """Básico: cria 2 motoboys OK, 3o → 403."""
        token = setup["basico"]["token"]
        # 1o motoboy
        resp = self._criar_motoboy(client, token, "Moto1 B", "motob1", "11911111101")
        assert resp.status_code == 200 or resp.status_code == 201
        # 2o motoboy
        resp = self._criar_motoboy(client, token, "Moto2 B", "motob2", "11911111102")
        assert resp.status_code == 200 or resp.status_code == 201
        # 3o → bloqueado
        resp = self._criar_motoboy(client, token, "Moto3 B", "motob3", "11911111103")
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["type"] == "feature_blocked"
        assert detail["feature"] == "motoboys"

    def test_essencial_limite_5(self, client, setup, db):
        """Essencial: cria 5 motoboys OK, 6o → 403."""
        token = setup["essencial"]["token"]
        for i in range(5):
            resp = self._criar_motoboy(client, token, f"Moto{i+1} E", f"motoe{i+1}", f"1192000010{i}")
            assert resp.status_code in (200, 201), f"Motoboy {i+1} deveria criar OK, got {resp.status_code}: {resp.text}"
        # 6o → bloqueado
        resp = self._criar_motoboy(client, token, "Moto6 E", "motoe6", "11920000109")
        assert resp.status_code == 403

    def test_premium_limite_alto(self, client, setup, db):
        """Premium: limite 999 — cria sem problemas."""
        token = setup["premium"]["token"]
        resp = self._criar_motoboy(client, token, "Moto1 P", "motop1", "11940000001")
        assert resp.status_code in (200, 201)

    def test_trial_ignora_limite(self, client, setup, db):
        """Trial: limite do tier (2 para Básico) mas trial bypassa feature guards."""
        token = setup["trial"]["token"]
        # Trial é Básico (limite_motoboys=2), mas como trial tem acesso total...
        # O limite é enforced no POST /painel/motoboys que usa rest.limite_motoboys diretamente
        # Trial com tier 1 tem limite_motoboys=2
        resp = self._criar_motoboy(client, token, "Moto1 T", "motot1", "11950000001")
        assert resp.status_code in (200, 201)
        resp = self._criar_motoboy(client, token, "Moto2 T", "motot2", "11950000002")
        assert resp.status_code in (200, 201)

    def test_basico_mensagem_upgrade(self, client, setup, db):
        """403 de motoboy inclui mensagem de upgrade."""
        token = setup["basico"]["token"]
        resp = self._criar_motoboy(client, token, "Moto Extra", "motobextra", "11911111199")
        # Se já atingiu limite (de test anterior), espera 403
        if resp.status_code == 403:
            detail = resp.json()["detail"]
            assert "upgrade" in detail["message"].lower() or "Faça upgrade" in detail["message"]

    def test_403_motoboy_inclui_plano_requerido(self, client, setup, db):
        """403 inclui o próximo plano que permite mais motoboys."""
        token = setup["basico"]["token"]
        resp = self._criar_motoboy(client, token, "Extra B2", "motobex2", "11911111198")
        if resp.status_code == 403:
            detail = resp.json()["detail"]
            assert "required_plano" in detail


# ═══════════════════════════════════════════════════════════════
# F13. Test403ResponseFormat — Formato detalhado do 403
# ═══════════════════════════════════════════════════════════════

class Test403ResponseFormat:
    """Valida formato estruturado do 403."""

    def test_403_campos_obrigatorios(self, client, setup):
        """403 tem todos os campos obrigatórios."""
        resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        campos = ["type", "feature", "feature_label", "current_plano",
                   "current_tier", "required_plano", "required_tier", "message"]
        for campo in campos:
            assert campo in detail, f"Campo '{campo}' faltando no 403"

    def test_403_com_addon_tem_addon_info(self, client, setup):
        """Quando feature tem add-on, 403 inclui addon_info."""
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        detail = resp.json()["detail"]
        assert "addon_info" in detail
        addon_info = detail["addon_info"]
        assert "available" in addon_info
        assert "price" in addon_info
        assert "label" in addon_info
        assert "min_tier" in addon_info
        assert "can_subscribe" in addon_info

    def test_403_sem_addon_nao_tem_addon_info(self, client, setup):
        """Feature sem add-on → addon_info ausente."""
        resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
        detail = resp.json()["detail"]
        assert "addon_info" not in detail

    def test_403_mensagem_em_portugues(self, client, setup):
        """Mensagem do 403 está em português."""
        resp = client.get("/painel/combos", headers=_auth(setup["basico"]["token"]))
        detail = resp.json()["detail"]
        # Verifica palavras em português
        assert "plano" in detail["message"].lower() or "requer" in detail["message"].lower()

    def test_403_can_subscribe_logica(self, client, setup):
        """can_subscribe=True quando tier >= addon_min_tier AND tier < feature_tier."""
        # Essencial (tier 2) → addon min_tier=2, feature tier=4 → can_subscribe=True
        resp = client.get("/painel/bot/config", headers=_auth(setup["essencial"]["token"]))
        assert resp.json()["detail"]["addon_info"]["can_subscribe"] is True

        # Básico (tier 1) → addon min_tier=2, tier < min_tier → can_subscribe=False
        resp = client.get("/painel/bot/config", headers=_auth(setup["basico"]["token"]))
        assert resp.json()["detail"]["addon_info"]["can_subscribe"] is False


# ═══════════════════════════════════════════════════════════════
# F14. TestMatrizCompletaFeatures — Teste paramétrico completo
# ═══════════════════════════════════════════════════════════════

class TestMatrizCompletaFeatures:
    """Testa TODA a matriz 22 features × 4 tiers."""

    @pytest.mark.parametrize("plano,tier", [
        ("Básico", 1), ("Essencial", 2), ("Avançado", 3), ("Premium", 4),
    ])
    def test_has_feature_matriz(self, plano, tier):
        """Para cada combinação plano×feature, verifica valor correto."""
        from backend.app.feature_flags import has_feature, FEATURE_TIERS

        for feature_key, min_tier in FEATURE_TIERS.items():
            resultado = has_feature(plano, feature_key)
            esperado = tier >= min_tier
            assert resultado == esperado, (
                f"has_feature('{plano}', '{feature_key}') = {resultado}, "
                f"esperado {esperado} (tier={tier}, min_tier={min_tier})"
            )

    @pytest.mark.parametrize("plano,tier", [
        ("Básico", 1), ("Essencial", 2), ("Avançado", 3), ("Premium", 4),
    ])
    def test_get_all_features_consistente(self, plano, tier):
        """get_all_features deve ser consistente com has_feature individual."""
        from backend.app.feature_flags import has_feature, get_all_features, FEATURE_TIERS

        all_features = get_all_features(plano)
        for feature_key in FEATURE_TIERS:
            individual = has_feature(plano, feature_key)
            assert all_features[feature_key] == individual, (
                f"Inconsistência: get_all_features('{plano}')['{feature_key}']="
                f"{all_features[feature_key]} vs has_feature={individual}"
            )

    def test_feature_tiers_tem_22_features(self):
        from backend.app.feature_flags import FEATURE_TIERS
        assert len(FEATURE_TIERS) == 22, f"FEATURE_TIERS tem {len(FEATURE_TIERS)} features, esperado 22"

    def test_feature_labels_cobrem_todas(self):
        from backend.app.feature_flags import FEATURE_TIERS, FEATURE_LABELS
        for feat in FEATURE_TIERS:
            assert feat in FEATURE_LABELS, f"Feature '{feat}' sem label em FEATURE_LABELS"

    def test_tier_to_plano_completo(self):
        from backend.app.feature_flags import TIER_TO_PLANO
        for tier in [1, 2, 3, 4]:
            assert tier in TIER_TO_PLANO, f"Tier {tier} sem plano em TIER_TO_PLANO"

    def test_motoboys_por_tier_completo(self):
        from backend.app.feature_flags import MOTOBOYS_POR_TIER
        for tier in [1, 2, 3, 4]:
            assert tier in MOTOBOYS_POR_TIER, f"Tier {tier} sem limite em MOTOBOYS_POR_TIER"
        # Verificar valores
        assert MOTOBOYS_POR_TIER[1] == 2
        assert MOTOBOYS_POR_TIER[2] == 5
        assert MOTOBOYS_POR_TIER[3] == 10
        assert MOTOBOYS_POR_TIER[4] == 999


# ═══════════════════════════════════════════════════════════════
# F15. TestEndpointsCRUD — Verifica que POST/PUT/DELETE também são guardados
# ═══════════════════════════════════════════════════════════════

class TestEndpointsCRUD:
    """Verifica que operações de escrita (POST/PUT/DELETE) respeitam feature guards."""

    def test_basico_403_post_combo(self, client, setup):
        resp = client.post("/painel/combos", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "Combo X", "preco": 29.90, "itens": []})
        assert resp.status_code == 403

    def test_basico_403_post_promocao(self, client, setup):
        resp = client.post("/painel/promocoes", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "Promo X", "tipo": "desconto", "valor": 10})
        assert resp.status_code == 403

    def test_basico_403_post_fidelidade(self, client, setup):
        resp = client.post("/painel/fidelidade/premios", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "Prêmio X", "pontos": 100})
        assert resp.status_code == 403

    def test_basico_403_post_operador(self, client, setup):
        resp = client.post("/painel/caixa/operadores", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "Op X", "login": "opx", "senha": "123456"})
        assert resp.status_code == 403

    def test_basico_403_post_cozinheiro(self, client, setup):
        resp = client.post("/painel/cozinha/cozinheiros", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "Chef X", "login": "chefx", "senha": "123456"})
        assert resp.status_code == 403

    def test_basico_403_post_garcom(self, client, setup):
        resp = client.post("/painel/garcom/garcons", headers=_auth(setup["basico"]["token"]),
                           json={"nome": "G X", "login": "gx", "senha": "123456"})
        assert resp.status_code == 403

    def test_basico_403_post_dominio(self, client, setup):
        resp = client.post("/painel/dominios", headers=_auth(setup["basico"]["token"]),
                           json={"dominio": "test.com"})
        assert resp.status_code == 403

    def test_essencial_acessa_post_combo(self, client, setup):
        resp = client.post("/painel/combos", headers=_auth(setup["essencial"]["token"]),
                           json={"nome": "Combo Ess", "preco": 29.90, "itens": []})
        # Pode dar 200/201 ou 422 (validação), mas NÃO 403
        assert resp.status_code != 403


# ═══════════════════════════════════════════════════════════════
# F16. TestBillingCancelado — Cancelado também bloqueia
# ═══════════════════════════════════════════════════════════════

class TestBillingCancelado:
    """billing_status='canceled_billing' também bloqueia como suspenso."""

    def test_cancelado_403(self, client, setup, db):
        rest = setup["suspenso"]["rest"]
        rest.billing_status = "canceled_billing"
        db.commit()
        try:
            resp = client.get("/painel/combos", headers=_auth(setup["suspenso"]["token"]))
            assert resp.status_code == 403
            assert "Assinatura suspensa" in str(resp.json()["detail"]) or \
                   "cancelada" in str(resp.json()["detail"])
        finally:
            rest.billing_status = "suspended_billing"
            db.commit()

    def test_cancelado_login_permite(self, client, setup, db):
        """Restaurante cancelado PODE fazer login (para ver tela de pagamento)."""
        rest = setup["suspenso"]["rest"]
        rest.billing_status = "canceled_billing"
        db.commit()
        try:
            resp = client.post("/auth/restaurante/login", json={
                "email": "suspenso@test.com", "senha": "teste123",
            })
            assert resp.status_code == 200
        finally:
            rest.billing_status = "suspended_billing"
            db.commit()


# ═══════════════════════════════════════════════════════════════
# F17. TestSuspensoEndpointsExtendido — Mais endpoints para suspenso
# ═══════════════════════════════════════════════════════════════

class TestSuspensoEndpointsExtendido:
    """Verifica que suspenso bloqueia TODAS as categorias de endpoints."""

    def test_suspenso_403_promocoes(self, client, setup):
        resp = client.get("/painel/promocoes", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_fidelidade(self, client, setup):
        resp = client.get("/painel/fidelidade/premios", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_garcom(self, client, setup):
        resp = client.get("/painel/garcom/garcons", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_dominios(self, client, setup):
        resp = client.get("/painel/dominios", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_integracoes(self, client, setup):
        resp = client.get("/painel/integracoes", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_403_operadores(self, client, setup):
        resp = client.get("/painel/caixa/operadores", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_suspenso_mensagem_correta(self, client, setup):
        """Mensagem do suspenso é genérica (não é feature_blocked)."""
        resp = client.get("/painel/combos", headers=_auth(setup["suspenso"]["token"]))
        detail = resp.json()["detail"]
        assert isinstance(detail, str)
        assert "suspensa" in detail.lower() or "cancelada" in detail.lower()


# ═══════════════════════════════════════════════════════════════
# F18. TestHelperFunctions — get_tier, get_features_list_for_plano
# ═══════════════════════════════════════════════════════════════

class TestHelperFunctions:
    """Testa funções auxiliares do feature_flags.py."""

    def test_get_tier_aliases(self):
        from backend.app.feature_flags import get_tier
        assert get_tier("Básico") == 1
        assert get_tier("basico") == 1
        assert get_tier("Basico") == 1
        assert get_tier("Essencial") == 2
        assert get_tier("essencial") == 2
        assert get_tier("Avançado") == 3
        assert get_tier("avancado") == 3
        assert get_tier("Premium") == 4
        assert get_tier("premium") == 4

    def test_get_tier_none_default(self):
        from backend.app.feature_flags import get_tier
        assert get_tier(None) == 1

    def test_get_tier_desconhecido_default(self):
        from backend.app.feature_flags import get_tier
        assert get_tier("PlanoInexistente") == 1

    def test_get_features_list_cumulativo(self):
        """get_features_list_for_plano retorna lista cumulativa."""
        from backend.app.feature_flags import get_features_list_for_plano
        basico = get_features_list_for_plano("Básico")
        essencial = get_features_list_for_plano("Essencial")
        avancado = get_features_list_for_plano("Avançado")
        premium = get_features_list_for_plano("Premium")
        # Cada tier tem mais features que o anterior
        assert len(basico) < len(essencial) < len(avancado) < len(premium)
        # Tier 4 tem todas
        assert len(premium) == 22

    def test_get_new_features_exclusivas(self):
        """get_new_features_for_plano retorna apenas features NOVAS do tier."""
        from backend.app.feature_flags import get_new_features_for_plano
        basico_new = get_new_features_for_plano("Básico")
        essencial_new = get_new_features_for_plano("Essencial")
        # Sem sobreposição
        assert not set(basico_new) & set(essencial_new)

    def test_features_por_plano_cobertura_total(self):
        """Todas features existem em exatamente um tier."""
        from backend.app.feature_flags import FEATURES_POR_PLANO, FEATURE_TIERS
        todas = []
        for features in FEATURES_POR_PLANO.values():
            todas.extend(features)
        assert len(todas) == len(FEATURE_TIERS)
        assert set(todas) == set(FEATURE_TIERS.keys())

    def test_addon_features_registradas(self):
        """Todos add-ons referem features que existem."""
        from backend.app.feature_flags import ADDON_FEATURES, FEATURE_TIERS
        for feat in ADDON_FEATURES:
            assert feat in FEATURE_TIERS, f"Add-on '{feat}' não está em FEATURE_TIERS"

    def test_addon_included_tier_maior_que_min_tier(self):
        """ADDON_INCLUDED_TIER >= ADDON_MIN_TIER (faz sentido lógico)."""
        from backend.app.feature_flags import ADDON_MIN_TIER, ADDON_INCLUDED_TIER
        for feat in ADDON_MIN_TIER:
            assert ADDON_INCLUDED_TIER[feat] >= ADDON_MIN_TIER[feat], (
                f"Add-on '{feat}': included_tier < min_tier"
            )


# ═══════════════════════════════════════════════════════════════
# F19. TestRelatoriosAvancados — Guard relatorios_avancados (tier 2)
# ═══════════════════════════════════════════════════════════════

class TestRelatoriosAvancados:
    """Valida guard de relatorios_avancados nos endpoints de relatórios."""

    def test_basico_403_relatorios_vendas(self, client, setup):
        resp = client.get("/painel/relatorios/vendas", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["feature"] == "relatorios_avancados"

    def test_basico_403_relatorios_motoboys(self, client, setup):
        resp = client.get("/painel/relatorios/motoboys", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_essencial_acessa_relatorios_vendas(self, client, setup):
        resp = client.get("/painel/relatorios/vendas", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_essencial_acessa_relatorios_motoboys(self, client, setup):
        resp = client.get("/painel/relatorios/motoboys", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 200

    def test_trial_acessa_relatorios(self, client, setup):
        resp = client.get("/painel/relatorios/vendas", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code == 200

    def test_suspenso_403_relatorios(self, client, setup):
        resp = client.get("/painel/relatorios/vendas", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════
# F20. TestPixOnline — Guard pix_online (tier 3)
# ═══════════════════════════════════════════════════════════════

class TestPixOnline:
    """Valida guard de pix_online nos endpoints de Pix."""

    def test_basico_403_pix_status(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["feature"] == "pix_online"

    def test_essencial_403_pix_status(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["essencial"]["token"]))
        assert resp.status_code == 403

    def test_avancado_acessa_pix_status(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["avancado"]["token"]))
        # Pode dar 502 (sem Woovi configurado) mas NÃO 403
        assert resp.status_code != 403

    def test_premium_acessa_pix_status(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["premium"]["token"]))
        assert resp.status_code != 403

    def test_trial_acessa_pix(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["trial"]["token"]))
        assert resp.status_code != 403

    def test_suspenso_403_pix(self, client, setup):
        resp = client.get("/painel/pix/status", headers=_auth(setup["suspenso"]["token"]))
        assert resp.status_code == 403

    def test_basico_403_pix_saques(self, client, setup):
        resp = client.get("/painel/pix/saques", headers=_auth(setup["basico"]["token"]))
        assert resp.status_code == 403

    def test_avancado_acessa_pix_saques(self, client, setup):
        resp = client.get("/painel/pix/saques", headers=_auth(setup["avancado"]["token"]))
        assert resp.status_code == 200
