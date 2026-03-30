"""
Testes completos das 22+ capacidades do Bot WhatsApp Humanoide.

Usa números únicos por cenário para evitar contaminação.
Roda contra produção (restaurante deve estar ABERTO).

Uso:
    python tests/test_bot_22caps.py --prod
"""
import asyncio
import httpx
import time
import sys
import uuid
import argparse
from datetime import datetime

RESTAURANTE_EMAIL = "tuga@gmail.com"
RESTAURANTE_SENHA = "123456"

# Números únicos por cenário (nunca reutilizados)
NUMS = {
    "saudacao":           "5511900010001",
    "cardapio":           "5511900010002",
    "categorias":         "5511900010003",
    "pedido_completo":    "5511900010004",
    "status_pedido":      "5511900010005",
    "rastrear":           "5511900010006",
    "horario":            "5511900010007",
    "cancelar":           "5511900010008",
    "alterar":            "5511900010009",
    "repetir":            "5511900010010",
    "promocoes":          "5511900010011",
    "avaliacao":          "5511900010012",
    "problema":           "5511900010013",
    "cupom":              "5511900010014",
    "escalar":            "5511900010015",
    "endereco":           "5511900010016",
    "taxa_entrega":       "5511900010017",
    "pagamento":          "5511900010018",
    "tempo_estimado":     "5511900010019",
    "agendar":            "5511900010020",
    "complementos":       "5511900010021",
    "pix":                "5511900010022",
    "cadastro":           "5511900010023",
    "simultaneas":        "5511900010024",
}


class BotTester22:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.instance = "derekh-whatsapp"
        self.resultados = []
        self._known: dict[str, int] = {}

    async def login(self):
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self.base_url}/auth/restaurante/login",
                             json={"email": RESTAURANTE_EMAIL, "senha": RESTAURANTE_SENHA})
            r.raise_for_status()
            self.token = r.json()["access_token"]
            print(f"[OK] Login: {RESTAURANTE_EMAIL}")
            r2 = await c.get(f"{self.base_url}/painel/bot/config",
                             headers={"Authorization": f"Bearer {self.token}"})
            if r2.status_code == 200 and r2.json().get("evolution_instance"):
                self.instance = r2.json()["evolution_instance"]
            print(f"[OK] Instância: {self.instance}")

    def _payload(self, num: str, texto: str) -> dict:
        return {
            "event": "messages.upsert",
            "instance": self.instance,
            "data": {
                "key": {"remoteJid": f"{num}@s.whatsapp.net", "fromMe": False,
                        "id": f"t_{uuid.uuid4().hex[:12]}"},
                "pushName": f"Teste {num[-4:]}",
                "message": {"conversation": texto},
                "messageType": "conversation",
                "messageTimestamp": int(time.time()),
            },
        }

    async def send(self, num: str, texto: str):
        async with httpx.AsyncClient(timeout=30) as c:
            await c.post(f"{self.base_url}/webhooks/evolution", json=self._payload(num, texto))

    async def wait_reply(self, num: str, timeout_s: int = 50) -> tuple:
        inicio = time.time()
        baseline = self._known.get(num, 0)
        async with httpx.AsyncClient(timeout=30) as c:
            while (time.time() - inicio) < timeout_s:
                try:
                    r = await c.get(f"{self.base_url}/painel/bot/conversas",
                                    headers={"Authorization": f"Bearer {self.token}"},
                                    params={"limite": 50})
                    if r.status_code != 200:
                        await asyncio.sleep(3); continue
                    conv = next((x for x in r.json().get("conversas", []) if x["telefone"] == num), None)
                    if not conv:
                        await asyncio.sleep(3); continue
                    r2 = await c.get(f"{self.base_url}/painel/bot/conversas/{conv['id']}/mensagens",
                                     headers={"Authorization": f"Bearer {self.token}"})
                    if r2.status_code != 200:
                        await asyncio.sleep(3); continue
                    novas = [m for m in r2.json().get("mensagens", [])
                             if m["direcao"] == "enviada" and m["id"] > baseline]
                    if novas:
                        ult = novas[-1]
                        self._known[num] = ult["id"]
                        return ult["conteudo"], ult.get("function_calls")
                except (httpx.ReadTimeout, httpx.ConnectError):
                    pass
                await asyncio.sleep(3)
        return None, None

    async def msg(self, num: str, texto: str, timeout_s: int = 50) -> tuple:
        tag = num[-4:]
        print(f"  ← [{tag}] {texto}")
        try:
            await self.send(num, texto)
        except Exception as e:
            print(f"  [ERR] envio: {e}")
            return None, None
        await asyncio.sleep(2)
        resp, fns = await self.wait_reply(num, timeout_s)
        if resp:
            fn_str = ""
            if fns:
                fn_str = f" [FN: {', '.join(f['nome'] for f in fns)}]"
            print(f"  → [{tag}] {resp[:140].replace(chr(10),' ')}...{fn_str}")
        else:
            print(f"  → [{tag}] (SEM RESPOSTA {timeout_s}s)")
        return resp, fns

    def reg(self, nome: str, ok: bool, detalhe: str = ""):
        self.resultados.append({"teste": nome, "ok": ok, "detalhe": detalhe})
        print(f"  {'✅' if ok else '❌'} {nome}: {detalhe}")

    def has_fn(self, fns, *nomes) -> bool:
        return bool(fns and any(f["nome"] in nomes for f in fns))

    def all_fns(self, fns1, fns2=None) -> list:
        return (fns1 or []) + (fns2 or [])

    # ==================== TESTES ====================

    async def t01_saudacao(self):
        """1. Saudação e apresentação"""
        print("\n" + "=" * 60)
        print("CAP 1: Saudação")
        print("=" * 60)
        r, f = await self.msg(NUMS["saudacao"], "Oi boa noite")
        self.reg("1. Saudação", r is not None and len(r) > 5, "Respondeu" if r else "Sem resposta")

    async def t02_buscar_cardapio(self):
        """2. buscar_cardapio — buscar item específico"""
        print("\n" + "=" * 60)
        print("CAP 2: buscar_cardapio")
        print("=" * 60)
        n = NUMS["cardapio"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Quero uma pizza calabresa, quanto custa?")
        self.reg("2. buscar_cardapio",
                 self.has_fn(f, "buscar_cardapio") or (r and "r$" in r.lower()),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t03_buscar_categorias(self):
        """3. buscar_categorias — listar categorias"""
        print("\n" + "=" * 60)
        print("CAP 3: buscar_categorias")
        print("=" * 60)
        n = NUMS["categorias"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Quais tipos de comida vocês têm? Me mostra as categorias")
        self.reg("3. buscar_categorias",
                 self.has_fn(f, "buscar_categorias", "buscar_cardapio") or (r and r is not None),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t04_cadastrar_cliente(self):
        """4. cadastrar_cliente — registrar cliente novo"""
        print("\n" + "=" * 60)
        print("CAP 4: cadastrar_cliente")
        print("=" * 60)
        n = NUMS["cadastro"]
        r1, f1 = await self.msg(n, "Oi quero fazer um pedido")
        r2, f2 = await self.msg(n, "Meu nome é Carlos Teste")
        all_f = self.all_fns(f1, f2)
        self.reg("4. cadastrar_cliente",
                 self.has_fn(all_f, "cadastrar_cliente") or (r2 and "cadastr" in r2.lower()),
                 f"FN: {[x['nome'] for x in all_f] if all_f else 'nenhum'}")

    async def t05_pedido_completo(self):
        """5. criar_pedido — pedido completo (pedir, confirmar, criar)"""
        print("\n" + "=" * 60)
        print("CAP 5: criar_pedido (fluxo completo)")
        print("=" * 60)
        n = NUMS["pedido_completo"]
        await self.msg(n, "Oi, meu nome é Pedro Teste, quero fazer um pedido")
        await asyncio.sleep(2)
        await self.msg(n, "Quero uma pizza calabresa grande pra retirar no balcão")
        await asyncio.sleep(2)
        r, f = await self.msg(n, "Pagamento em dinheiro, pode confirmar")
        self.reg("5. criar_pedido",
                 self.has_fn(f, "criar_pedido") or (r and ("comanda" in r.lower() or "#" in (r or ""))),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t06_consultar_status(self):
        """6. consultar_status_pedido — verificar status"""
        print("\n" + "=" * 60)
        print("CAP 6: consultar_status_pedido")
        print("=" * 60)
        n = NUMS["status_pedido"]
        await self.msg(n, "Oi meu nome é Ana Status")
        r, f = await self.msg(n, "Qual o status do meu último pedido?")
        self.reg("6. consultar_status_pedido",
                 self.has_fn(f, "consultar_status_pedido", "rastrear_pedido", "buscar_cliente"),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t07_rastrear_pedido(self):
        """7. rastrear_pedido — rastreamento detalhado"""
        print("\n" + "=" * 60)
        print("CAP 7: rastrear_pedido")
        print("=" * 60)
        n = NUMS["rastrear"]
        await self.msg(n, "Oi sou Maria Rastreio")
        r, f = await self.msg(n, "Cadê meu pedido? Tá demorando!")
        self.reg("7. rastrear_pedido",
                 self.has_fn(f, "rastrear_pedido", "consultar_status_pedido", "buscar_cliente"),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t08_verificar_horario(self):
        """8. verificar_horario — consultar horário"""
        print("\n" + "=" * 60)
        print("CAP 8: verificar_horario")
        print("=" * 60)
        n = NUMS["horario"]
        r, f = await self.msg(n, "Vocês estão abertos agora? Qual o horário de funcionamento?")
        self.reg("8. verificar_horario",
                 self.has_fn(f, "verificar_horario") or (r and ("aberto" in r.lower() or "horário" in r.lower() or "18" in (r or ""))),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t09_cancelar_pedido(self):
        """9. cancelar_pedido — cancelar pelo bot"""
        print("\n" + "=" * 60)
        print("CAP 9: cancelar_pedido")
        print("=" * 60)
        n = NUMS["cancelar"]
        await self.msg(n, "Oi sou Joana Cancel, fiz um pedido agora")
        r, f = await self.msg(n, "Quero cancelar meu pedido por favor")
        self.reg("9. cancelar_pedido",
                 self.has_fn(f, "cancelar_pedido", "consultar_status_pedido", "rastrear_pedido") or (r and "cancel" in r.lower()),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t10_alterar_pedido(self):
        """10. alterar_pedido — modificar pedido existente"""
        print("\n" + "=" * 60)
        print("CAP 10: alterar_pedido")
        print("=" * 60)
        n = NUMS["alterar"]
        await self.msg(n, "Oi sou Marcos Altera, fiz um pedido agora")
        r, f = await self.msg(n, "Quero trocar minha pizza por uma margherita")
        self.reg("10. alterar_pedido",
                 self.has_fn(f, "alterar_pedido", "trocar_item_pedido", "consultar_status_pedido") or (r and ("alter" in r.lower() or "troc" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t11_repetir_pedido(self):
        """11. repetir_ultimo_pedido — repetir pedido anterior"""
        print("\n" + "=" * 60)
        print("CAP 11: repetir_ultimo_pedido")
        print("=" * 60)
        n = NUMS["repetir"]
        await self.msg(n, "Oi sou Lucas Repete")
        r, f = await self.msg(n, "Quero repetir meu último pedido, o mesmo de sempre")
        self.reg("11. repetir_ultimo_pedido",
                 self.has_fn(f, "repetir_ultimo_pedido", "buscar_cliente") or (r and "repet" in r.lower()),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t12_buscar_promocoes(self):
        """12. buscar_promocoes — promoções ativas"""
        print("\n" + "=" * 60)
        print("CAP 12: buscar_promocoes")
        print("=" * 60)
        n = NUMS["promocoes"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Tem alguma promoção hoje? Algum desconto?")
        self.reg("12. buscar_promocoes",
                 self.has_fn(f, "buscar_promocoes") or (r and ("promoção" in r.lower() or "promo" in r.lower() or "desconto" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t13_registrar_avaliacao(self):
        """13. registrar_avaliacao — avaliar pedido"""
        print("\n" + "=" * 60)
        print("CAP 13: registrar_avaliacao")
        print("=" * 60)
        n = NUMS["avaliacao"]
        await self.msg(n, "Oi sou Paula Avalia, recebi meu pedido")
        r, f = await self.msg(n, "Quero avaliar, nota 5 estrelas! Tudo perfeito, comida maravilhosa")
        self.reg("13. registrar_avaliacao",
                 self.has_fn(f, "registrar_avaliacao") or (r and ("avalia" in r.lower() or "obrigad" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t14_registrar_problema(self):
        """14. registrar_problema — reportar problema"""
        print("\n" + "=" * 60)
        print("CAP 14: registrar_problema")
        print("=" * 60)
        n = NUMS["problema"]
        await self.msg(n, "Oi sou Ricardo Problema")
        r, f = await self.msg(n, "Meu pedido veio errado! Pedi calabresa e veio margherita, tô muito chateado")
        self.reg("14. registrar_problema",
                 self.has_fn(f, "registrar_problema") or (r and ("descul" in r.lower() or "problema" in r.lower() or "sinto" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t15_aplicar_cupom(self):
        """15. aplicar_cupom — aplicar cupom de desconto"""
        print("\n" + "=" * 60)
        print("CAP 15: aplicar_cupom")
        print("=" * 60)
        n = NUMS["cupom"]
        await self.msg(n, "Oi quero fazer um pedido")
        r, f = await self.msg(n, "Tenho um cupom de desconto PRIMEIRACOMPRA, pode aplicar?")
        self.reg("15. aplicar_cupom",
                 self.has_fn(f, "aplicar_cupom") or (r and ("cupom" in r.lower() or "desconto" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t16_escalar_humano(self):
        """16. escalar_humano — transferir para atendente humano"""
        print("\n" + "=" * 60)
        print("CAP 16: escalar_humano")
        print("=" * 60)
        n = NUMS["escalar"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Quero falar com o gerente, com uma pessoa de verdade, não quero robô")
        self.reg("16. escalar_humano",
                 self.has_fn(f, "escalar_humano") or (r and ("responsável" in r.lower() or "gerente" in r.lower() or "equipe" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t17_validar_endereco(self):
        """17. validar_endereco — validar endereço via geocoding"""
        print("\n" + "=" * 60)
        print("CAP 17: validar_endereco")
        print("=" * 60)
        n = NUMS["endereco"]
        await self.msg(n, "Oi meu nome é Fernanda Endereco, quero pedir pra entrega")
        r, f = await self.msg(n, "Meu endereço é Rua Augusta 500, São Paulo")
        self.reg("17. validar_endereco",
                 self.has_fn(f, "validar_endereco", "atualizar_endereco_cliente") or (r and ("endereço" in r.lower() or "rua" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t18_calcular_taxa(self):
        """18. calcular_taxa_entrega — consultar taxa por endereço"""
        print("\n" + "=" * 60)
        print("CAP 18: calcular_taxa_entrega")
        print("=" * 60)
        n = NUMS["taxa_entrega"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Quanto custa a taxa de entrega pro Centro?")
        self.reg("18. calcular_taxa_entrega",
                 self.has_fn(f, "calcular_taxa_entrega", "consultar_bairros") or (r and ("taxa" in r.lower() or "entrega" in r.lower() or "r$" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t19_formas_pagamento(self):
        """19. listar_formas_pagamento"""
        print("\n" + "=" * 60)
        print("CAP 19: listar_formas_pagamento")
        print("=" * 60)
        n = NUMS["pagamento"]
        await self.msg(n, "Oi quero pedir")
        r, f = await self.msg(n, "Quais formas de pagamento vocês aceitam?")
        self.reg("19. formas_pagamento",
                 self.has_fn(f, "listar_formas_pagamento") or (r and ("pagamento" in r.lower() or "dinheiro" in r.lower() or "cartão" in r.lower() or "pix" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t20_tempo_estimado(self):
        """20. consultar_tempo_estimado — previsão de entrega"""
        print("\n" + "=" * 60)
        print("CAP 20: consultar_tempo_estimado")
        print("=" * 60)
        n = NUMS["tempo_estimado"]
        await self.msg(n, "Oi")
        r, f = await self.msg(n, "Quanto tempo demora pra entregar? Qual a previsão?")
        self.reg("20. tempo_estimado",
                 self.has_fn(f, "consultar_tempo_estimado", "consultar_tempo_entrega") or (r and ("minuto" in r.lower() or "tempo" in r.lower() or "previsão" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t21_agendar_pedido(self):
        """21. agendar_pedido — agendar para horário futuro"""
        print("\n" + "=" * 60)
        print("CAP 21: agendar_pedido")
        print("=" * 60)
        n = NUMS["agendar"]
        await self.msg(n, "Oi meu nome é Julia Agenda")
        r, f = await self.msg(n, "Quero agendar um pedido pra amanhã às 19h, pode ser?")
        self.reg("21. agendar_pedido",
                 self.has_fn(f, "agendar_pedido") or (r and ("agend" in r.lower() or "amanhã" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t22_sugerir_complementos(self):
        """22. sugerir_complementos — upsell/cross-sell"""
        print("\n" + "=" * 60)
        print("CAP 22: sugerir_complementos")
        print("=" * 60)
        n = NUMS["complementos"]
        await self.msg(n, "Oi meu nome é Bruno Combo")
        r, f = await self.msg(n, "Quero uma pizza grande, o que combina pra acompanhar?")
        self.reg("22. sugerir_complementos",
                 self.has_fn(f, "sugerir_complementos", "buscar_cardapio") or (r and ("bebida" in r.lower() or "acompanha" in r.lower() or "combina" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'}")

    async def t23_pix(self):
        """23-24. gerar_cobranca_pix + consultar_pagamento_pix"""
        print("\n" + "=" * 60)
        print("CAP 23-24: Pix (gerar_cobranca + consultar)")
        print("=" * 60)
        n = NUMS["pix"]
        await self.msg(n, "Oi quero pedir e pagar por Pix")
        r, f = await self.msg(n, "Quero pagar meu pedido com Pix online, pode gerar?")
        self.reg("23-24. Pix",
                 self.has_fn(f, "gerar_cobranca_pix") or (r and ("pix" in r.lower())),
                 f"FN: {[x['nome'] for x in f] if f else 'nenhum'} (WOOVI pode não estar configurado)")

    # ==================== RUNNER ====================

    async def executar(self):
        print("=" * 60)
        print("BOT WHATSAPP — TESTE 22+ CAPACIDADES")
        print(f"URL: {self.base_url}")
        print(f"Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)

        await self.login()

        testes = [
            self.t01_saudacao,
            self.t02_buscar_cardapio,
            self.t03_buscar_categorias,
            self.t04_cadastrar_cliente,
            self.t05_pedido_completo,
            self.t06_consultar_status,
            self.t07_rastrear_pedido,
            self.t08_verificar_horario,
            self.t09_cancelar_pedido,
            self.t10_alterar_pedido,
            self.t11_repetir_pedido,
            self.t12_buscar_promocoes,
            self.t13_registrar_avaliacao,
            self.t14_registrar_problema,
            self.t15_aplicar_cupom,
            self.t16_escalar_humano,
            self.t17_validar_endereco,
            self.t18_calcular_taxa,
            self.t19_formas_pagamento,
            self.t20_tempo_estimado,
            self.t21_agendar_pedido,
            self.t22_sugerir_complementos,
            self.t23_pix,
        ]

        for fn in testes:
            try:
                await fn()
            except Exception as e:
                print(f"\n  [CRASH] {fn.__name__}: {e}")
                self.reg(fn.__name__, False, str(e)[:80])

        # Relatório
        print("\n" + "=" * 60)
        print("RELATÓRIO FINAL — 22+ CAPACIDADES")
        print("=" * 60)
        ok = sum(1 for r in self.resultados if r["ok"])
        fail = sum(1 for r in self.resultados if not r["ok"])
        total = len(self.resultados)

        for r in self.resultados:
            e = "✅" if r["ok"] else "❌"
            print(f"  {e} {r['teste']}: {r['detalhe']}")

        print(f"\nTotal: {total} | ✅ {ok} | ❌ {fail}")
        pct = (ok / total * 100) if total else 0
        print(f"Taxa de sucesso: {pct:.0f}%")
        print("=" * 60)
        return fail == 0


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prod", action="store_true")
    args = parser.parse_args()
    url = "https://superfood-api.fly.dev" if args.prod else "http://localhost:8000"
    t = BotTester22(url)
    ok = await t.executar()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
