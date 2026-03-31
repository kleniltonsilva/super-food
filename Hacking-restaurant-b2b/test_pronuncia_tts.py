"""
test_pronuncia_tts.py — Teste de pronúncia Fish Audio S2-Pro em produção.

Gera áudios com frases contendo termos tech (iFood, KDS, Rappi, etc.)
e envia via Evolution API para o número de teste no WhatsApp.

Uso:
    # Local (com .env configurado):
    python test_pronuncia_tts.py

    # Em produção (fly ssh):
    fly ssh console --app derekh-crm -C "python test_pronuncia_tts.py"

    # Enviar para número específico:
    python test_pronuncia_tts.py --numero 5511999999999

    # Só gerar áudios (sem enviar WhatsApp):
    python test_pronuncia_tts.py --sem-envio
"""
import os
import sys
import time
import base64
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_pronuncia")

# Frases de teste — cada uma testa um ou mais termos
FRASES_TESTE = [
    ("iFood", "Vocês não estão no iFood ainda, não é?"),
    ("iFood+Rappi", "A Derekh Food é complemento ao iFood e ao Rappi."),
    ("KDS", "O KDS da cozinha mostra os pedidos em tempo real."),
    ("Bridge", "O Bridge captura pedidos automaticamente da impressora."),
    ("Setup", "Depois do setup de 48 horas tá tudo rodando."),
    ("QR Code", "O cliente escaneia o QR Code e faz o pedido na hora."),
    ("PWA", "Funciona como PWA, instala direto no celular sem precisar de loja."),
    ("Derekh", "A Derekh Food é o sistema completo de delivery para restaurantes."),
    ("Completo", "Com a Derekh, você não precisa mais depender só do iFood. Tem KDS, Bridge, app de motoboy, tudo integrado."),
]


def gerar_audio_fish(texto: str, emocao: str = "amigavel") -> bytes | None:
    """Gera áudio via Fish Audio S2-Pro usando o módulo fish_tts."""
    try:
        from crm.fish_tts import gerar_audio_fish_async
        import asyncio
        return asyncio.run(gerar_audio_fish_async(texto, emocao))
    except ImportError:
        log.warning("crm.fish_tts não disponível, tentando direto...")

    # Fallback: chamar API diretamente
    try:
        import httpx
    except ImportError:
        log.error("httpx não instalado")
        return None

    fish_key = os.environ.get("FISH_API_KEY", "")
    if not fish_key:
        log.error("FISH_API_KEY não configurada")
        return None

    voice_id = os.environ.get("FISH_VOICE_ID", "")

    # Aplicar pronúncias manualmente
    pronuncias = [
        ("Derekh Food", "Dérikh Food"), ("Derekh", "Dérikh"),
        ("iFood", "áiFud"), ("ifood", "áifud"),
        ("Rappi", "Rápi"), ("rappi", "rápi"),
        ("KDS", "cá dê ésse"), ("PWA", "pê dáblio ei"),
        ("QR Code", "quiú ár côde"), ("QR code", "quiú ár côde"),
        ("Bridge", "Bridji"), ("bridge", "bridji"),
        ("Setup", "Setáp"), ("setup", "setáp"),
    ]
    for escrita, pronuncia in pronuncias:
        texto = texto.replace(escrita, pronuncia)

    payload = {
        "text": f"[amigável] {texto}",
        "format": "mp3",
        "latency": "balanced",
        "mp3_bitrate": 128,
    }
    if voice_id:
        payload["reference_id"] = voice_id

    try:
        resp = httpx.post(
            "https://api.fish.audio/v1/tts",
            headers={
                "Authorization": f"Bearer {fish_key}",
                "Content-Type": "application/json",
                "model": "s2-pro",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        audio = resp.content
        if audio and len(audio) > 100:
            return audio
        log.warning(f"Áudio muito pequeno: {len(audio)} bytes")
        return None
    except Exception as e:
        log.error(f"Erro Fish Audio: {e}")
        return None


def enviar_audio_evolution(numero: str, audio_bytes: bytes) -> bool:
    """Envia áudio PTT via Evolution API."""
    try:
        import httpx
    except ImportError:
        log.error("httpx não instalado")
        return False

    url = os.environ.get("EVOLUTION_API_URL", "")
    key = os.environ.get("EVOLUTION_API_KEY", "")
    inst = os.environ.get("EVOLUTION_INSTANCE", "")

    # Tentar carregar do DB se não estiver no env
    if not url or not key or not inst:
        try:
            from crm.database import obter_configuracao
            url = url or obter_configuracao("evolution_api_url") or ""
            key = key or obter_configuracao("evolution_api_key") or ""
            inst = inst or obter_configuracao("evolution_instance") or ""
        except Exception:
            pass

    if not all([url, key, inst]):
        log.error(f"Evolution não configurada (url={bool(url)}, key={bool(key)}, inst={bool(inst)})")
        return False

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    try:
        resp = httpx.post(
            f"{url}/message/sendWhatsAppAudio/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"number": numero, "audio": audio_b64, "encoding": True},
            timeout=30,
        )
        resp.raise_for_status()
        msg_id = resp.json().get("key", {}).get("id", "desconhecido")
        log.info(f"  Áudio enviado: msg_id={msg_id}")
        return True
    except Exception as e:
        log.error(f"  Erro envio Evolution: {e}")
        return False


def enviar_texto_evolution(numero: str, texto: str) -> bool:
    """Envia mensagem de texto via Evolution API (para legendar o áudio)."""
    try:
        import httpx
    except ImportError:
        return False

    url = os.environ.get("EVOLUTION_API_URL", "")
    key = os.environ.get("EVOLUTION_API_KEY", "")
    inst = os.environ.get("EVOLUTION_INSTANCE", "")

    if not url or not key or not inst:
        try:
            from crm.database import obter_configuracao
            url = url or obter_configuracao("evolution_api_url") or ""
            key = key or obter_configuracao("evolution_api_key") or ""
            inst = inst or obter_configuracao("evolution_instance") or ""
        except Exception:
            pass

    if not all([url, key, inst]):
        return False

    try:
        resp = httpx.post(
            f"{url}/message/sendText/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"number": numero, "text": texto},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Teste de pronúncia TTS Fish Audio")
    parser.add_argument("--numero", default="351933358929",
                        help="Número WhatsApp para envio (padrão: dono)")
    parser.add_argument("--sem-envio", action="store_true",
                        help="Só gerar áudios, não enviar via WhatsApp")
    parser.add_argument("--salvar", action="store_true",
                        help="Salvar áudios como .mp3 local")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("TESTE DE PRONÚNCIA TTS — Fish Audio S2-Pro")
    log.info(f"Frases: {len(FRASES_TESTE)} | Envio WA: {'NÃO' if args.sem_envio else 'SIM'}")
    log.info("=" * 60)

    resultados = {"sucesso": 0, "erro": 0, "enviados": 0}

    for i, (termos, frase) in enumerate(FRASES_TESTE, 1):
        log.info(f"\n[{i}/{len(FRASES_TESTE)}] Termos: {termos}")
        log.info(f"  Frase: {frase}")

        audio = gerar_audio_fish(frase)

        if audio:
            kb = len(audio) / 1024
            log.info(f"  Áudio gerado: {kb:.1f} KB")
            resultados["sucesso"] += 1

            if args.salvar:
                fname = f"teste_pronuncia_{i}_{termos.replace('+', '_').lower()}.mp3"
                with open(fname, "wb") as f:
                    f.write(audio)
                log.info(f"  Salvo: {fname}")

            if not args.sem_envio:
                # Enviar legenda antes do áudio
                enviar_texto_evolution(args.numero, f"[TESTE {i}] {termos}: {frase}")
                time.sleep(1)

                if enviar_audio_evolution(args.numero, audio):
                    resultados["enviados"] += 1

                time.sleep(2)  # Delay entre envios
        else:
            log.error(f"  FALHA ao gerar áudio")
            resultados["erro"] += 1

    log.info("\n" + "=" * 60)
    log.info("RESULTADO FINAL:")
    log.info(f"  Gerados: {resultados['sucesso']}/{len(FRASES_TESTE)}")
    log.info(f"  Erros: {resultados['erro']}")
    if not args.sem_envio:
        log.info(f"  Enviados WA: {resultados['enviados']}")
    log.info("=" * 60)

    if resultados["erro"] > 0:
        log.warning("⚠ Verifique FISH_API_KEY e FISH_VOICE_ID")

    return 0 if resultados["erro"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
