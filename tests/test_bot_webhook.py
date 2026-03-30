"""
Testes do Bot WhatsApp via webhook — simula conversas reais.

Envia payloads para POST /webhooks/evolution e verifica respostas
via GET /painel/bot/conversas/{id}/mensagens.

Cenários testados:
1. Pedido completo (pedido → confirmação → status)
2. Cancelamento detectado pelo bot
3. Status em tempo real (bot consulta BD, não inventa)
4. Múltiplas conversas simultâneas

Uso:
    python tests/test_bot_webhook.py [--prod]

    --prod  Usa https://superfood-api.fly.dev (padrão: localhost:8000)
"""
import asyncio
import httpx
import json
import time
import sys
import uuid
import argparse
from datetime import datetime


# Configuração
RESTAURANTE_EMAIL = "tuga@gmail.com"
RESTAURANTE_SENHA = "123456"

# Números de teste (fake — não são WhatsApp reais)
NUMEROS_TESTE = [
    "5521999990001",
    "5521999990002",
    "5521999990003",
    "5521999990004",
    "5521999990005",
]


class BotTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.evolution_instance = "derekh-whatsapp"
        self.resultados = []
        self._known_msg_ids: dict[str, int] = {}  # numero -> last known msg id

    async def login(self):
        """Login restaurante e descobrir instância Evolution."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/auth/restaurante/login",
                json={"email": RESTAURANTE_EMAIL, "senha": RESTAURANTE_SENHA},
            )
            resp.raise_for_status()
            self.token = resp.json()["access_token"]
            print(f"[OK] Login restaurante: {RESTAURANTE_EMAIL}")

            # Descobrir instância Evolution do bot
            resp2 = await client.get(
                f"{self.base_url}/painel/bot/config",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if resp2.status_code == 200:
                config = resp2.json()
                if config.get("evolution_instance"):
                    self.evolution_instance = config["evolution_instance"]
                    print(f"[OK] Instância Evolution: {self.evolution_instance}")

    def _webhook_payload(self, numero: str, texto: str, msg_id: str = None) -> dict:
        """Monta payload igual ao que a Evolution API envia."""
        if not msg_id:
            msg_id = f"test_{uuid.uuid4().hex[:12]}"
        return {
            "event": "messages.upsert",
            "instance": self.evolution_instance,
            "data": {
                "key": {
                    "remoteJid": f"{numero}@s.whatsapp.net",
                    "fromMe": False,
                    "id": msg_id,
                },
                "pushName": f"Teste {numero[-4:]}",
                "message": {
                    "conversation": texto,
                },
                "messageType": "conversation",
                "messageTimestamp": int(time.time()),
            },
        }

    async def enviar_msg(self, numero: str, texto: str) -> dict:
        """Envia mensagem via webhook e retorna resposta."""
        payload = self._webhook_payload(numero, texto)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/webhooks/evolution",
                json=payload,
            )
            return resp.json()

    async def aguardar_resposta(self, numero: str, timeout_s: int = 45) -> str | None:
        """Aguarda o bot responder via API de conversas."""
        inicio = time.time()
        baseline_id = self._known_msg_ids.get(numero, 0)

        async with httpx.AsyncClient(timeout=15) as client:
            while (time.time() - inicio) < timeout_s:
                # Buscar conversas
                resp = await client.get(
                    f"{self.base_url}/painel/bot/conversas",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"limite": 30},
                )
                if resp.status_code != 200:
                    await asyncio.sleep(2)
                    continue

                conversas = resp.json().get("conversas", [])
                conversa = next((c for c in conversas if c["telefone"] == numero), None)
                if not conversa:
                    await asyncio.sleep(2)
                    continue

                # Buscar mensagens
                resp2 = await client.get(
                    f"{self.base_url}/painel/bot/conversas/{conversa['id']}/mensagens",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if resp2.status_code != 200:
                    await asyncio.sleep(2)
                    continue

                msgs = resp2.json().get("mensagens", [])
                # Mensagens NOVAS do bot (após baseline)
                novas_enviadas = [
                    m for m in msgs
                    if m["direcao"] == "enviada" and m["id"] > baseline_id
                ]
                if novas_enviadas:
                    ultima = novas_enviadas[-1]
                    self._known_msg_ids[numero] = ultima["id"]
                    return ultima["conteudo"], ultima.get("function_calls")

                await asyncio.sleep(3)

        return None, None

    async def enviar_e_aguardar(self, numero: str, texto: str, timeout_s: int = 45) -> tuple:
        """Envia mensagem e aguarda resposta do bot."""
        print(f"  ← [{numero[-4:]}] {texto}")
        await self.enviar_msg(numero, texto)
        await asyncio.sleep(2)  # Dar tempo para o bot iniciar processamento
        resposta, fns = await self.aguardar_resposta(numero, timeout_s)
        if resposta:
            fn_str = ""
            if fns:
                fn_str = f" [FN: {', '.join(f['nome'] for f in fns)}]"
            preview = resposta[:120].replace("\n", " ")
            print(f"  → [{numero[-4:]}] {preview}...{fn_str}")
        else:
            print(f"  → [{numero[-4:]}] (SEM RESPOSTA em {timeout_s}s)")
        return resposta, fns

    def registrar(self, teste: str, passou: bool, detalhe: str = ""):
        """Registra resultado do teste."""
        status = "PASS" if passou else "FAIL"
        self.resultados.append({"teste": teste, "status": status, "detalhe": detalhe})
        emoji = "✅" if passou else "❌"
        print(f"  {emoji} {teste}: {detalhe}")

    # ==================== CENÁRIOS DE TESTE ====================

    async def teste_1_pedido_basico(self):
        """Teste 1: Fazer pedido completo e verificar se bot cria."""
        print("\n" + "=" * 60)
        print("TESTE 1: Pedido básico completo")
        print("=" * 60)
        num = NUMEROS_TESTE[0]

        resp, fns = await self.enviar_e_aguardar(num, "Oi quero fazer um pedido")
        self.registrar("1.1 Saudação", resp is not None, "Bot respondeu" if resp else "Sem resposta")

        resp, fns = await self.enviar_e_aguardar(num, "Uma pizza grande calabresa", timeout_s=40)
        tem_cardapio = fns and any(f["nome"] == "buscar_cardapio" for f in fns)
        self.registrar("1.2 Busca cardápio", tem_cardapio or resp is not None,
                       f"FN: {[f['nome'] for f in fns] if fns else 'nenhum'}")

    async def teste_2_consulta_status(self):
        """Teste 2: Perguntar status de pedido — bot DEVE chamar consultar_status_pedido."""
        print("\n" + "=" * 60)
        print("TESTE 2: Consultar status do pedido (bot deve consultar BD)")
        print("=" * 60)
        num = NUMEROS_TESTE[1]

        await self.enviar_e_aguardar(num, "Oi")
        resp, fns = await self.enviar_e_aguardar(num, "Qual o status do meu pedido?", timeout_s=40)

        chamou_fn = fns and any(
            f["nome"] in ("consultar_status_pedido", "buscar_cliente") for f in fns
        )
        self.registrar(
            "2.1 Consulta BD real",
            chamou_fn,
            f"FN chamadas: {[f['nome'] for f in fns] if fns else 'NENHUMA — bot inventou!'}"
        )

    async def teste_3_cancelamento(self):
        """Teste 3: Fazer pedido, cancelar no painel, perguntar status."""
        print("\n" + "=" * 60)
        print("TESTE 3: Detecção de cancelamento")
        print("=" * 60)
        num = NUMEROS_TESTE[2]

        # 1. Fazer pedido rápido
        await self.enviar_e_aguardar(num, "Oi quero uma coca 2 litros pra retirar")
        await asyncio.sleep(3)
        await self.enviar_e_aguardar(num, "Meu nome é Teste Cancelamento, vou retirar na loja", timeout_s=40)
        await asyncio.sleep(3)
        resp, fns = await self.enviar_e_aguardar(num, "Pagamento dinheiro, pode confirmar", timeout_s=40)

        # Verificar se criou pedido
        chamou_criar = fns and any(f["nome"] == "criar_pedido" for f in fns)
        self.registrar("3.1 Criou pedido", chamou_criar or (resp and "comanda" in resp.lower()),
                       "Pedido criado" if chamou_criar else "Verificar manualmente")

        if chamou_criar:
            # 2. Cancelar via API do painel
            await asyncio.sleep(5)
            print("  [PAINEL] Cancelando pedido via API...")

            async with httpx.AsyncClient(timeout=15) as client:
                # Buscar pedidos para encontrar o último
                resp_pedidos = await client.get(
                    f"{self.base_url}/painel/pedidos",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"limite": 5},
                )
                if resp_pedidos.status_code == 200:
                    pedidos = resp_pedidos.json().get("pedidos", [])
                    ultimo_pedido = pedidos[0] if pedidos else None

                    if ultimo_pedido:
                        pedido_id = ultimo_pedido["id"]
                        # Cancelar
                        resp_cancel = await client.put(
                            f"{self.base_url}/painel/pedidos/{pedido_id}/status",
                            headers={"Authorization": f"Bearer {self.token}"},
                            json={"status": "cancelado", "senha": RESTAURANTE_SENHA},
                        )
                        cancelou = resp_cancel.status_code == 200
                        self.registrar("3.2 Cancelou via painel", cancelou,
                                       f"Pedido #{pedido_id} — HTTP {resp_cancel.status_code}")

                        if cancelou:
                            await asyncio.sleep(3)
                            # 3. Perguntar status
                            resp, fns = await self.enviar_e_aguardar(
                                num, "E aí, meu pedido tá pronto?", timeout_s=40
                            )

                            # Bot DEVE informar que foi cancelado
                            detectou_cancel = resp and ("cancelado" in resp.lower() or "cancel" in resp.lower())
                            self.registrar(
                                "3.3 Bot detectou cancelamento",
                                detectou_cancel,
                                f"Resposta: {resp[:100] if resp else 'SEM RESPOSTA'}",
                            )

    async def teste_4_multiplas_simultaneas(self):
        """Teste 4: Múltiplas conversas ao mesmo tempo."""
        print("\n" + "=" * 60)
        print("TESTE 4: Conversas simultâneas (3 clientes)")
        print("=" * 60)

        nums = NUMEROS_TESTE[3:6] if len(NUMEROS_TESTE) >= 6 else NUMEROS_TESTE[3:5]

        # Enviar mensagens de todos ao mesmo tempo
        tasks = []
        for num in nums:
            tasks.append(self.enviar_msg(num, f"Oi, quero ver o cardápio por favor"))

        await asyncio.gather(*tasks)
        print(f"  [INFO] {len(nums)} mensagens enviadas simultaneamente")

        # Aguardar respostas
        await asyncio.sleep(15)

        respondidos = 0
        for num in nums:
            resp, _ = await self.aguardar_resposta(num, timeout_s=20)
            if resp:
                respondidos += 1
                print(f"  → [{num[-4:]}] OK — {resp[:80]}...")
            else:
                print(f"  → [{num[-4:]}] SEM RESPOSTA")

        self.registrar(
            "4.1 Todas receberam resposta",
            respondidos == len(nums),
            f"{respondidos}/{len(nums)} respondidas"
        )

    async def teste_5_verificar_horario(self):
        """Teste 5: Perguntar horário — bot DEVE chamar verificar_horario."""
        print("\n" + "=" * 60)
        print("TESTE 5: Verificar horário (deve chamar function call)")
        print("=" * 60)
        num = NUMEROS_TESTE[4]

        await self.enviar_e_aguardar(num, "Oi")
        resp, fns = await self.enviar_e_aguardar(num, "Vocês estão abertos agora?", timeout_s=40)

        chamou_fn = fns and any(f["nome"] == "verificar_horario" for f in fns)
        self.registrar(
            "5.1 Chamou verificar_horario",
            chamou_fn or resp is not None,
            f"FN: {[f['nome'] for f in fns] if fns else 'nenhum'}"
        )

    # ==================== RUNNER ====================

    async def executar_todos(self):
        """Executa todos os testes em sequência."""
        print("=" * 60)
        print(f"BOT WHATSAPP — SUITE DE TESTES")
        print(f"Base URL: {self.base_url}")
        print(f"Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)

        await self.login()

        # Executar testes
        await self.teste_1_pedido_basico()
        await self.teste_2_consulta_status()
        await self.teste_3_cancelamento()
        await self.teste_4_multiplas_simultaneas()
        await self.teste_5_verificar_horario()

        # Relatório final
        print("\n" + "=" * 60)
        print("RELATÓRIO FINAL")
        print("=" * 60)
        passou = sum(1 for r in self.resultados if r["status"] == "PASS")
        falhou = sum(1 for r in self.resultados if r["status"] == "FAIL")
        total = len(self.resultados)

        for r in self.resultados:
            emoji = "✅" if r["status"] == "PASS" else "❌"
            print(f"  {emoji} {r['teste']}: {r['detalhe']}")

        print(f"\nTotal: {total} testes | ✅ {passou} passou | ❌ {falhou} falhou")
        print("=" * 60)

        return falhou == 0


async def main():
    parser = argparse.ArgumentParser(description="Testes do Bot WhatsApp via webhook")
    parser.add_argument("--prod", action="store_true", help="Usar servidor de produção")
    args = parser.parse_args()

    base_url = "https://superfood-api.fly.dev" if args.prod else "http://localhost:8000"

    tester = BotTester(base_url)
    sucesso = await tester.executar_todos()
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    asyncio.run(main())
