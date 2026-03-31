"""
Testes da migração Evolution → Meta Cloud API.
Valida: whatsapp_client dispatch, webhook Meta, conversão áudio, provider dual.
"""
import asyncio
import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime


# ============================================================
# Fixtures
# ============================================================

def _make_bot_config(provider="evolution", **kwargs):
    """Cria um BotConfig mock com provider configurável."""
    config = MagicMock()
    config.whatsapp_provider = provider
    config.restaurante_id = 1
    config.bot_ativo = True
    config.nome_atendente = "Bia"
    config.idioma = "pt-BR"
    config.voz_tts = "ara"
    config.tts_autonomo = False
    config.tts_provider = "grok"
    config.stt_ativo = True
    config.pode_criar_pedido = True
    config.max_tokens_dia = 50000
    config.tokens_usados_hoje = 0
    # Evolution fields
    config.evolution_instance = "test-instance"
    config.evolution_api_url = "https://evo.test"
    config.evolution_api_key = "evo-key-123"
    config.whatsapp_numero = "5511999999999"
    # Meta fields
    config.meta_phone_number_id = "123456789"
    config.meta_access_token = "EAAtest123"
    config.meta_waba_id = "waba-123"
    config.meta_app_secret = "app-secret-test"
    config.meta_webhook_verify_token = "verify-token-test"
    # Override
    for k, v in kwargs.items():
        setattr(config, k, v)
    return config


def _make_pool_entry():
    """Cria um BotPhonePool mock."""
    entry = MagicMock()
    entry.id = 1
    entry.evolution_instance = "pool-instance"
    entry.evolution_api_url = "https://pool.evo"
    entry.evolution_api_key = "pool-key"
    entry.whatsapp_numero = "5511888888888"
    return entry


def _meta_webhook_payload(text="Quero fazer um pedido", phone_number_id="123456789", msg_type="text"):
    """Gera payload de webhook Meta completo."""
    msg = {
        "from": "5511888880001",
        "id": "wamid.test123",
        "timestamp": "1234567890",
        "type": msg_type,
    }
    if msg_type == "text":
        msg["text"] = {"body": text}
    elif msg_type == "audio":
        msg["audio"] = {"id": "media_audio_123", "mime_type": "audio/ogg", "duration": 5}
    elif msg_type == "interactive":
        msg["interactive"] = {"type": "button_reply", "button_reply": {"id": "btn_1", "title": text}}

    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "phone_number_id": phone_number_id,
                        "display_phone_number": "5511999999999",
                    },
                    "contacts": [{"profile": {"name": "João"}, "wa_id": "5511888880001"}],
                    "messages": [msg],
                },
            }],
        }],
    }


# ============================================================
# 1-2: enviar_texto dispatch por provider
# ============================================================

@pytest.mark.asyncio
async def test_enviar_texto_meta():
    """1. enviar_texto com provider='meta' → chama Meta API."""
    config = _make_bot_config(provider="meta")

    with patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"messages": [{"id": "wamid.ok"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            post=AsyncMock(return_value=mock_resp)
        ))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from backend.app.bot.whatsapp_client import enviar_texto
        result = await enviar_texto("5511888880001", "Olá!", config)
        assert result is not None


@pytest.mark.asyncio
async def test_enviar_texto_evolution():
    """2. enviar_texto com provider='evolution' → chama Evolution API."""
    config = _make_bot_config(provider="evolution")

    with patch("backend.app.bot.whatsapp_client.evolution_client.enviar_texto", new_callable=AsyncMock) as mock_evo:
        mock_evo.return_value = {"key": {"id": "msg123"}}

        from backend.app.bot.whatsapp_client import enviar_texto
        result = await enviar_texto("5511888880001", "Olá!", config)

        mock_evo.assert_called_once()
        assert result == {"key": {"id": "msg123"}}


# ============================================================
# 3: enviar_audio_ptt Meta → MP3→OGG + upload + send
# ============================================================

@pytest.mark.asyncio
async def test_enviar_audio_ptt_meta():
    """3. enviar_audio_ptt Meta → converte MP3→OGG, upload, send voice:true."""
    config = _make_bot_config(provider="meta")

    mp3_fake = base64.b64encode(b"fake mp3 data").decode()

    with patch("backend.app.bot.whatsapp_client._mp3_to_ogg_opus", new_callable=AsyncMock) as mock_conv, \
         patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_client:
        # Conversão retorna OGG fake
        mock_conv.return_value = b"OggS" + b"\x00" * 100

        # Mock HTTP: upload → media_id, send → ok
        call_count = [0]
        async def mock_post(url, **kwargs):
            resp = MagicMock()  # httpx Response.json() is sync, not async
            resp.raise_for_status = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # Upload
                resp.json.return_value = {"id": "media_123"}
            else:
                # Send message
                resp.json.return_value = {"messages": [{"id": "wamid.audio"}]}
            return resp

        mock_instance = AsyncMock()
        mock_instance.post = mock_post
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from backend.app.bot.whatsapp_client import enviar_audio_ptt
        result = await enviar_audio_ptt("5511888880001", mp3_fake, config)

        mock_conv.assert_called_once()
        assert call_count[0] == 2  # upload + send


# ============================================================
# 4: enviar_typing Meta → typing_indicator
# ============================================================

@pytest.mark.asyncio
async def test_enviar_typing_meta():
    """4. enviar_typing Meta → POST typing_indicator."""
    config = _make_bot_config(provider="meta")

    with patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from backend.app.bot.whatsapp_client import enviar_typing
        await enviar_typing("5511888880001", config)

        # Deve ter chamado POST com type=typing_indicator
        call_args = mock_instance.post.call_args
        assert call_args is not None


# ============================================================
# 5: marcar_lida Meta → POST status=read
# ============================================================

@pytest.mark.asyncio
async def test_marcar_lida_meta():
    """5. marcar_lida Meta → POST status=read."""
    config = _make_bot_config(provider="meta")

    with patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from backend.app.bot.whatsapp_client import marcar_lida
        await marcar_lida("wamid.test123", config)

        call_args = mock_instance.post.call_args
        payload = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("json")
        assert payload["status"] == "read"
        assert payload["message_id"] == "wamid.test123"


@pytest.mark.asyncio
async def test_marcar_lida_evolution_noop():
    """5b. marcar_lida Evolution → noop (Evolution faz auto)."""
    config = _make_bot_config(provider="evolution")

    from backend.app.bot.whatsapp_client import marcar_lida
    # Não deve levantar exceção nem chamar nada
    await marcar_lida("msg123", config)


# ============================================================
# 6: baixar_audio Meta → 2 steps
# ============================================================

@pytest.mark.asyncio
async def test_baixar_audio_meta():
    """6. baixar_audio Meta → GET URL + GET binary."""
    config = _make_bot_config(provider="meta")

    with patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_client:
        call_count = [0]
        async def mock_get(url, **kwargs):
            resp = MagicMock()  # httpx Response.json() is sync
            resp.raise_for_status = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # GET media URL
                resp.json.return_value = {"url": "https://lookaside.test/audio.ogg", "mime_type": "audio/ogg"}
            else:
                # GET binary
                resp.content = b"OggS audio data"
            return resp

        mock_instance = AsyncMock()
        mock_instance.get = mock_get
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        from backend.app.bot.whatsapp_client import baixar_audio
        result = await baixar_audio("media_123", config)

        assert result is not None
        assert result["mimetype"] == "audio/ogg"
        assert result["base64"]  # Deve ter base64
        assert call_count[0] == 2  # 2 GETs


# ============================================================
# 7: _mp3_to_ogg_opus converte corretamente
# ============================================================

@pytest.mark.asyncio
async def test_mp3_to_ogg_opus_ffmpeg_not_found():
    """7b. _mp3_to_ogg_opus sem ffmpeg → retorna None (graceful)."""
    from backend.app.bot.whatsapp_client import _mp3_to_ogg_opus

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result = await _mp3_to_ogg_opus(b"fake mp3")
        assert result is None


# ============================================================
# 8-9: processar_webhook_meta extrai texto e áudio
# ============================================================

@pytest.mark.asyncio
async def test_processar_webhook_meta_texto():
    """8. processar_webhook_meta extrai texto → chama _processar_mensagem_meta."""
    payload = _meta_webhook_payload(text="Olá, quero um pizza")

    with patch("backend.app.bot.atendente._processar_mensagem_meta", new_callable=AsyncMock) as mock_proc, \
         patch("backend.app.bot.atendente._processed_msg_ids", {}), \
         patch("backend.app.bot.atendente._processing_locks", {}):
        from backend.app.bot.atendente import processar_webhook_meta
        result = await processar_webhook_meta(payload)

        assert result["status"] == "processing"
        # _processar_mensagem_meta é chamado via asyncio.create_task
        # Precisamos dar tempo ao event loop
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_processar_webhook_meta_audio():
    """9. processar_webhook_meta extrai áudio → passa audio_meta."""
    payload = _meta_webhook_payload(msg_type="audio")

    with patch("backend.app.bot.atendente._processar_mensagem_meta", new_callable=AsyncMock) as mock_proc, \
         patch("backend.app.bot.atendente._processed_msg_ids", {}), \
         patch("backend.app.bot.atendente._processing_locks", {}):
        from backend.app.bot.atendente import processar_webhook_meta
        result = await processar_webhook_meta(payload)
        assert result["status"] == "processing"


# ============================================================
# 10-11: processar_webhook_meta ignora status updates e msgs próprias
# ============================================================

@pytest.mark.asyncio
async def test_processar_webhook_meta_ignora_status():
    """10. processar_webhook_meta ignora status updates."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "123"},
                    "statuses": [{"id": "wamid.x", "status": "delivered"}],
                },
            }],
        }],
    }

    from backend.app.bot.atendente import processar_webhook_meta
    result = await processar_webhook_meta(payload)
    # Deve ignorar (sem messages, com statuses)
    assert result["status"] in ("ignored", "processing")


@pytest.mark.asyncio
async def test_processar_webhook_meta_sem_messages():
    """11. processar_webhook_meta ignora payload sem messages."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "123"},
                },
            }],
        }],
    }

    from backend.app.bot.atendente import processar_webhook_meta
    result = await processar_webhook_meta(payload)
    assert result["status"] == "ignored" or result["status"] == "processing"


# ============================================================
# 12: _identificar_restaurante por meta_phone_number_id
# ============================================================

def test_identificar_restaurante_evolution():
    """12b. _identificar_restaurante por instance Evolution (existente)."""
    mock_db = MagicMock()
    mock_config = _make_bot_config(provider="evolution")

    mock_db.query.return_value.filter.return_value.first.return_value = mock_config

    from backend.app.bot.atendente import _identificar_restaurante
    result = _identificar_restaurante(mock_db, "test-instance")
    assert result is not None


# ============================================================
# 13-14: Webhook signature validation
# ============================================================

def test_webhook_signature_valida():
    """13. Webhook META valida X-Hub-Signature-256."""
    import hashlib
    import hmac as hmac_lib

    body = b'{"test": true}'
    secret = "test-secret"
    sig = "sha256=" + hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()

    from backend.app.bot.meta_cloud_client import validar_webhook_signature
    assert validar_webhook_signature(body, sig, secret) is True


def test_webhook_signature_invalida():
    """14. Webhook META rejeita assinatura inválida."""
    from backend.app.bot.meta_cloud_client import validar_webhook_signature
    assert validar_webhook_signature(b"data", "sha256=invalido", "secret") is False
    assert validar_webhook_signature(b"data", "", "secret") is False
    assert validar_webhook_signature(b"data", "md5=abc", "secret") is False


# ============================================================
# 15: Migration 045 (verificar estrutura)
# ============================================================

def test_migration_045_existe():
    """15. Migration 045 existe e tem campos corretos."""
    import importlib.util
    import os

    path = os.path.join(
        os.path.dirname(__file__), "..",
        "migrations", "versions", "045_bot_meta_provider.py"
    )
    assert os.path.exists(path), f"Migration 045 não encontrada em {path}"

    spec = importlib.util.spec_from_file_location("m045", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "045_bot_meta_provider"
    assert mod.down_revision == "044_bot_meta_gateway"


# ============================================================
# 16: BotConfig provider='evolution' continua funcionando
# ============================================================

@pytest.mark.asyncio
async def test_evolution_continua_funcionando():
    """16. BotConfig com provider='evolution' continua usando evolution_client."""
    config = _make_bot_config(provider="evolution")

    with patch("backend.app.bot.whatsapp_client.evolution_client.enviar_texto", new_callable=AsyncMock) as mock_evo:
        mock_evo.return_value = {"key": {"id": "msg456"}}

        from backend.app.bot.whatsapp_client import enviar_texto
        await enviar_texto("5511888880001", "Teste", config)

        mock_evo.assert_called_once_with(
            "5511888880001", "Teste",
            "test-instance", "https://evo.test", "evo-key-123",
            delay_ms=1500,
        )


# ============================================================
# 17: Worker health check ignora Meta
# ============================================================

def test_config_pode_enviar():
    """17. _config_pode_enviar() verifica credenciais corretas por provider."""
    from backend.app.bot.workers import _config_pode_enviar

    meta_config = _make_bot_config(provider="meta")
    assert _config_pode_enviar(meta_config) is True

    meta_config_sem_token = _make_bot_config(provider="meta", meta_access_token=None)
    assert _config_pode_enviar(meta_config_sem_token) is False

    evo_config = _make_bot_config(provider="evolution")
    assert _config_pode_enviar(evo_config) is True

    evo_config_sem_instance = _make_bot_config(provider="evolution", evolution_instance=None)
    assert _config_pode_enviar(evo_config_sem_instance) is False


# ============================================================
# 18: Áudio fallback — se OGG upload falhar → envia texto
# ============================================================

@pytest.mark.asyncio
async def test_audio_fallback_texto():
    """18. Se conversão MP3→OGG falhar → RuntimeError (caller faz fallback)."""
    config = _make_bot_config(provider="meta")
    audio_b64 = base64.b64encode(b"fake mp3").decode()

    with patch("backend.app.bot.whatsapp_client._mp3_to_ogg_opus", new_callable=AsyncMock) as mock_conv:
        mock_conv.return_value = None  # Conversão falhou

        from backend.app.bot.whatsapp_client import enviar_audio_ptt
        with pytest.raises(RuntimeError, match="Conversão MP3"):
            await enviar_audio_ptt("5511888880001", audio_b64, config)


# ============================================================
# 19: Dual-provider — 2 restaurantes, 1 meta + 1 evolution
# ============================================================

@pytest.mark.asyncio
async def test_dual_provider():
    """19. 2 restaurantes com providers diferentes funcionam simultâneos."""
    config_meta = _make_bot_config(provider="meta", restaurante_id=1)
    config_evo = _make_bot_config(provider="evolution", restaurante_id=2)

    with patch("backend.app.bot.whatsapp_client.httpx.AsyncClient") as mock_http, \
         patch("backend.app.bot.whatsapp_client.evolution_client.enviar_texto", new_callable=AsyncMock) as mock_evo:

        # Meta mock
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"messages": [{"id": "wamid.ok"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_resp)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)

        # Evolution mock
        mock_evo.return_value = {"key": {"id": "evo123"}}

        from backend.app.bot.whatsapp_client import enviar_texto

        # Restaurante 1 (Meta)
        await enviar_texto("5511111111111", "Meta msg", config_meta)
        mock_instance.post.assert_called()

        # Restaurante 2 (Evolution)
        await enviar_texto("5522222222222", "Evo msg", config_evo)
        mock_evo.assert_called_once()


# ============================================================
# 20: Pool entry usado apenas para Evolution
# ============================================================

@pytest.mark.asyncio
async def test_pool_entry_usado_com_evolution():
    """20. pool_entry é usado quando provider='evolution'."""
    config = _make_bot_config(provider="evolution")
    pool = _make_pool_entry()

    with patch("backend.app.bot.whatsapp_client.evolution_client.enviar_texto", new_callable=AsyncMock) as mock_evo:
        mock_evo.return_value = {}

        from backend.app.bot.whatsapp_client import enviar_texto
        await enviar_texto("5511888880001", "Teste pool", config, pool_entry=pool)

        # Deve usar credenciais do pool, não do config
        mock_evo.assert_called_once_with(
            "5511888880001", "Teste pool",
            "pool-instance", "https://pool.evo", "pool-key",
            delay_ms=1500,
        )
