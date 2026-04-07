"""
app.py - Derekh CRM — FastAPI entry point + todas as rotas
"""
import sys
import os
import json
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
import secrets
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import FastAPI, Request, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crm.database import (
    init_pool, close_pool, init_schema, criar_lead_quiz,
    kpis_dashboard, funil_pipeline, distribuicao_segmento,
    top_cidades, followups_hoje, leads_quentes_sem_contato,
    stats_delivery, stats_delivery_por_cidade, cidades_escaneadas_ifood, top_categorias_ifood,
    buscar_leads, listar_ufs_disponiveis, listar_cidades_disponiveis,
    obter_lead, obter_interacoes_lead, obter_socios_lead,
    atualizar_status_pipeline, agendar_followup,
    registrar_interacao, atualizar_notas,
    leads_por_pipeline, contagem_pipeline,
    listar_email_templates, obter_email_template,
    criar_email_template, atualizar_email_template, deletar_email_template,
    listar_campanhas, obter_campanha, criar_campanha,
    atualizar_status_campanha,
    listar_sequencias, obter_sequencia, criar_sequencia,
    adicionar_etapa_sequencia, inscrever_leads_sequencia,
    obter_configuracoes_todas, salvar_configuracao,
    cidade_tem_delivery_verificado,
    # Outreach (Fase 7)
    get_conn, marcar_email_aberto, marcar_email_clique, buscar_email_por_tracking,
    opt_out_lead, stats_outreach, emails_enviados_hoje,
    listar_outreach_pendentes, listar_outreach_futuras,
    leads_para_outreach, cancelar_outreach_lead, atualizar_tier_lead,
    # WhatsApp (Fase 7)
    listar_conversas_wa, obter_conversa_wa, stats_wa,
    # Agente (Fase 7)
    listar_experimentos, listar_decisoes_pendentes,
    aprovar_decisao, rejeitar_decisao, obter_ultimo_relatorio,
    # Autopilot
    autopilot_metricas, autopilot_funil, autopilot_config,
    autopilot_decisoes_recentes, autopilot_leads_quentes,
    autopilot_conversas_formatadas, autopilot_conversa_detalhe,
    atualizar_conversa_wa,
    # Outreach Regras
    listar_outreach_regras_todas, criar_outreach_regra,
    atualizar_outreach_regra, deletar_outreach_regra,
    leads_novos_sem_outreach,
    # Email Inbox
    listar_email_threads, obter_email_thread,
    marcar_thread_lida, marcar_thread_starred,
    arquivar_thread, categorizar_thread,
    contar_threads_por_categoria,
    # P2-P5: Funil completo, scoring, conversão
    conversas_handoff_sem_resposta,
    registrar_evento_lead,
    registrar_conversao, buscar_lead_por_cnpj,
    # Sync API
    upsert_leads_batch,
)
from crm.models import (
    PIPELINE_STATUS, PIPELINE_LABELS, PIPELINE_CORES,
    SEGMENTOS, SEGMENTO_LABELS, SEGMENTO_CORES,
    TIPOS_INTERACAO, CANAIS, RESULTADOS_INTERACAO,
    STATUS_CAMPANHA_LABELS,
)

# Scanner (PostgreSQL direto)
from db_pg import (
    init_pg, stats_cidades_scanner,
    criar_scan_job, obter_scan_job, listar_scan_jobs,
    obter_scan_logs, existe_scan_ativo,
    atualizar_scan_job,
)

# ============================================================
# AUTENTICAÇÃO — Senha de acesso ao CRM
# ============================================================
CRM_PASSWORD = os.environ.get("CRM_PASSWORD", "893618@")
CRM_SESSION_SECRET = os.environ.get("CRM_SESSION_SECRET", secrets.token_hex(32))
CRM_SYNC_API_KEY = os.environ.get("CRM_SYNC_API_KEY", "")

# Sessões ativas (token → True)
_active_sessions: dict[str, bool] = {}

# Rotas públicas (sem autenticação)
PUBLIC_PATHS = {
    "/login",
    "/tracking/",         # Pixel/clique/unsub (prefixo)
    "/webhooks/",         # Webhooks Resend outbound + inbound (prefixo)
    "/wa-sales/webhook",  # Webhook WhatsApp (prefixo)
    "/api/leads/quiz",    # Quiz diagnóstico landing page (público)
    "/api/leads/sync",    # Sync API (autenticado por API key, não por sessão)
    "/api/health/",       # Health checks (público)
}


def _is_public(path: str) -> bool:
    """Verifica se o path é público (sem autenticação)."""
    if path == "/login":
        return True
    for prefix in PUBLIC_PATHS:
        if prefix.endswith("/") and path.startswith(prefix):
            return True
    if path == "/wa-sales/webhook":
        return True
    if path == "/api/leads/quiz":
        return True
    if path == "/api/wa/migrar-numero":
        return True
    if path.startswith("/api/leads/") and path.endswith("/conversao"):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Rotas públicas passam direto
        if _is_public(path) or path.startswith("/static"):
            return await call_next(request)

        # Verificar cookie de sessão
        session_token = request.cookies.get("crm_session", "")
        if session_token and session_token in _active_sessions:
            return await call_next(request)

        # Não autenticado → redirecionar para login
        if request.method == "GET":
            return RedirectResponse("/login", status_code=302)
        else:
            return JSONResponse({"erro": "Não autenticado"}, status_code=401)


app = FastAPI(title="Derekh CRM")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://superfood-api.fly.dev",
        "https://derekhfood.com.br",
        "http://localhost:8000",
        "http://localhost:5173",
    ],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(AuthMiddleware)

CRM_DIR = os.path.dirname(os.path.abspath(__file__))

# Static files
static_dir = os.path.join(CRM_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(CRM_DIR, "templates"))


# ============================================================
# FILTROS JINJA
# ============================================================

def format_number(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

def format_currency(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def format_date(value):
    if not value:
        return ""
    return str(value)[:10]

def format_datetime(value):
    if not value:
        return ""
    return str(value)[:16]

def format_time(value):
    if not value:
        return ""
    s = str(value)
    # Extract HH:MM from datetime string
    if "T" in s:
        return s.split("T")[1][:5]
    if " " in s:
        return s.split(" ")[1][:5]
    return s[:5]

templates.env.filters["format_number"] = format_number
templates.env.filters["format_currency"] = format_currency
templates.env.filters["format_date"] = format_date
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_time"] = format_time
templates.env.globals["PIPELINE_LABELS"] = PIPELINE_LABELS
templates.env.globals["SEGMENTO_LABELS"] = SEGMENTO_LABELS
templates.env.globals["SEGMENTO_CORES"] = SEGMENTO_CORES


# ============================================================
# LIFECYCLE
# ============================================================

@app.on_event("startup")
async def startup():
    init_pool()
    init_schema()
    # Pool PG para scanner — com tratamento de erro
    try:
        init_pg()
        print("[STARTUP] Pool PostgreSQL (scanner) inicializado")
    except Exception as e:
        print(f"[STARTUP] AVISO: Pool PostgreSQL (scanner) falhou: {e}")
        print("[STARTUP] Scanner ficará indisponível até corrigir DATABASE_URL")
    # Outreach: respeitar configuração do banco (NÃO forçar ativação)
    from crm.database import obter_configuracao, salvar_configuracao
    _outreach_status = (obter_configuracao("outreach_ativo") or "false").lower()
    print(f"[STARTUP] outreach_ativo = {_outreach_status}")

    # Workers em background
    import asyncio
    asyncio.create_task(_outreach_loop())
    asyncio.create_task(_agente_loop())
    asyncio.create_task(_validacao_loop())
    asyncio.create_task(_auto_import_loop())
    asyncio.create_task(_brain_loop())


async def _outreach_loop():
    """Worker que executa ações de outreach pendentes a cada 5 minutos."""
    import asyncio
    await asyncio.sleep(10)  # Esperar app inicializar
    while True:
        try:
            from crm.outreach_engine import executar_acoes_pendentes
            stats = await asyncio.to_thread(executar_acoes_pendentes)
            if stats.get("executadas", 0) > 0 or stats.get("erros", 0) > 0:
                print(f"[OUTREACH-WORKER] {stats}")
        except Exception as e:
            print(f"[OUTREACH-WORKER] Erro: {e}")
        await asyncio.sleep(300)  # 5 minutos


async def _agente_loop():
    """Worker que executa ciclo diário do agente às 06:00."""
    import asyncio
    from datetime import datetime
    await asyncio.sleep(30)
    ultimo_dia = None
    while True:
        agora = datetime.now()
        if agora.hour == 6 and ultimo_dia != agora.date():
            try:
                from crm.agente_autonomo import ciclo_diario
                resultado = await asyncio.to_thread(ciclo_diario)
                print(f"[AGENTE-WORKER] Ciclo diário concluído: {resultado.get('relatorio_id')}")
                ultimo_dia = agora.date()
            except Exception as e:
                print(f"[AGENTE-WORKER] Erro: {e}")
        await asyncio.sleep(60)  # Verifica a cada 1 minuto

async def _validacao_loop():
    """Worker que valida contatos de leads a cada 6 horas.
    Roda em thread separada para NÃO bloquear o event loop do uvicorn."""
    import asyncio
    await asyncio.sleep(120)  # Esperar app inicializar
    while True:
        try:
            loop = asyncio.get_running_loop()
            from crm.contact_validator import validar_lote
            stats = await loop.run_in_executor(
                None, lambda: validar_lote(limite=200)
            )
            if stats.get("validados", 0) > 0:
                print(f"[VALIDATOR-WORKER] {stats}")
        except Exception as e:
            print(f"[VALIDATOR-WORKER] Erro: {e}")
        await asyncio.sleep(21600)  # 6 horas


async def _auto_import_loop():
    """Worker que auto-importa leads novos para outreach a cada 30 minutos.
    Verifica se outreach está ativo, busca leads sem ações e cria sequências."""
    import asyncio
    await asyncio.sleep(60)  # Esperar app inicializar
    while True:
        try:
            stats = await asyncio.to_thread(_auto_import_sync)
            if stats and stats.get("leads", 0) > 0:
                print(f"[AUTO-IMPORT] Importados {stats['leads']} leads, {stats['acoes']} ações criadas")
        except Exception as e:
            print(f"[AUTO-IMPORT] Erro: {e}")

        await asyncio.sleep(1800)  # 30 minutos


def _auto_import_sync() -> dict:
    """Versão sync do auto-import para rodar em thread."""
    from crm.database import obter_configuracao, leads_novos_sem_outreach
    from crm.outreach_engine import criar_sequencia_com_regras

    outreach_ativo = (obter_configuracao("outreach_ativo") or "false").lower() == "true"
    if not outreach_ativo:
        return {"leads": 0, "acoes": 0}

    leads = leads_novos_sem_outreach(50)
    if not leads:
        return {"leads": 0, "acoes": 0}

    total_acoes = 0
    for lead in leads:
        acoes = criar_sequencia_com_regras(lead["id"], lead)
        total_acoes += len(acoes)

    return {"leads": len(leads), "acoes": total_acoes}


async def _brain_loop():
    """Worker Brain Loop — orquestra validação WA, outreach multi-canal e handoff.
    Roda a cada 10 minutos. Conecta todos os componentes de forma autônoma."""
    import asyncio
    await asyncio.sleep(45)  # Esperar app + outros workers inicializarem
    print("[BRAIN-LOOP] Iniciado — ciclo a cada 10 minutos")
    while True:
        try:
            from crm.brain_loop import ciclo_brain
            stats = await ciclo_brain()
            total = sum(v for v in stats.values() if isinstance(v, int))
            if total > 0:
                print(f"[BRAIN-LOOP] Ciclo: {stats}")
        except Exception as e:
            print(f"[BRAIN-LOOP] Erro: {e}")
        await asyncio.sleep(600)  # 10 minutos


@app.on_event("shutdown")
async def shutdown():
    close_pool()


# ============================================================
# LOGIN / LOGOUT
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, erro: str = ""):
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login — Derekh CRM</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {{
                theme: {{ extend: {{ colors: {{
                    dk: {{ bg: '#060a10', bg2: '#0d1219', bg3: '#151c26', accent: '#00d4aa', text: '#e6edf3', dim: '#7d8590', border: '#1e2531' }}
                }} }} }}
            }}
        </script>
    </head>
    <body class="bg-dk-bg min-h-screen flex items-center justify-center">
        <div class="bg-dk-bg2 border border-dk-border rounded-2xl p-8 w-full max-w-sm shadow-xl">
            <div class="text-center mb-6">
                <div class="text-3xl font-bold text-dk-accent mb-1">Derekh CRM</div>
                <p class="text-dk-dim text-sm">Sales Autopilot</p>
            </div>
            {'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-red-300 text-sm text-center">Senha incorreta</div>' if erro else ''}
            <form method="POST" action="/login">
                <label class="block text-dk-dim text-xs uppercase tracking-wider mb-2">Senha de acesso</label>
                <input type="password" name="senha" autofocus required
                    class="w-full bg-dk-bg3 border border-dk-border rounded-lg px-4 py-3 text-dk-text focus:outline-none focus:border-dk-accent transition mb-4"
                    placeholder="Digite a senha">
                <button type="submit"
                    class="w-full bg-dk-accent hover:bg-dk-accent/80 text-dk-bg font-bold py-3 rounded-lg transition">
                    Entrar
                </button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.post("/login")
async def login_submit(senha: str = Form(...)):
    if senha.strip() == CRM_PASSWORD:
        token = secrets.token_hex(32)
        _active_sessions[token] = True
        response = RedirectResponse("/", status_code=302)
        response.set_cookie(
            key="crm_session", value=token,
            httponly=True, samesite="lax",
            max_age=86400 * 7,  # 7 dias
        )
        return response
    return RedirectResponse("/login?erro=1", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("crm_session", "")
    _active_sessions.pop(token, None)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("crm_session")
    return response


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    kpis = kpis_dashboard()
    funil = funil_pipeline()
    segmentos = distribuicao_segmento()
    cidades = top_cidades(10)
    followups = followups_hoje()
    quentes = leads_quentes_sem_contato()

    # Delivery stats
    delivery = stats_delivery()
    delivery_cidades = stats_delivery_por_cidade(50)
    cidades_ifood = cidades_escaneadas_ifood()
    ifood_categorias = top_categorias_ifood(10)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "kpis": kpis,
        "funil": funil,
        "segmentos": segmentos,
        "cidades": cidades,
        "followups": followups,
        "quentes": quentes,
        "delivery": delivery,
        "delivery_cidades": delivery_cidades,
        "cidades_ifood": cidades_ifood,
        "ifood_categorias": ifood_categorias,
        "funil_json": json.dumps(funil, default=str),
        "segmentos_json": json.dumps(segmentos, default=str),
        "cidades_json": json.dumps(cidades, default=str),
        "delivery_json": json.dumps(delivery, default=str),
        "delivery_cidades_json": json.dumps(delivery_cidades, default=str),
        "ifood_categorias_json": json.dumps(ifood_categorias, default=str),
        "pagina_ativa": "dashboard",
    })


# ============================================================
# API DELIVERY STATS
# ============================================================

@app.get("/api/stats/delivery")
async def api_stats_delivery(cidade: str = "", uf: str = ""):
    """Stats de delivery filtrados por cidade/uf (para AJAX do dashboard)."""
    result = stats_delivery(
        cidade=cidade if cidade else None,
        uf=uf if uf else None
    )
    return JSONResponse(result)


# ============================================================
# BUSCA DE LEADS
# ============================================================

@app.get("/busca", response_class=HTMLResponse)
async def busca(
    request: Request,
    uf: str = "", cidade: str = "", segmento: str = "",
    status_pipeline: str = "", score_min: str = "", score_max: str = "",
    tem_ifood: str = "", tem_rappi: str = "", tem_99food: str = "",
    eh_rede: str = "", q: str = "", pagina: int = 1,
):
    filtros = {}
    for key, val in [("uf", uf), ("cidade", cidade), ("segmento", segmento),
                     ("status_pipeline", status_pipeline), ("score_min", score_min),
                     ("score_max", score_max), ("tem_ifood", tem_ifood),
                     ("tem_rappi", tem_rappi), ("tem_99food", tem_99food),
                     ("eh_rede", eh_rede), ("q", q)]:
        if val:
            filtros[key] = val

    por_pagina = 50
    leads, total = buscar_leads(filtros, pagina, por_pagina)
    total_paginas = math.ceil(total / por_pagina) if total > 0 else 1
    ufs = listar_ufs_disponiveis()
    cidades_list = listar_cidades_disponiveis(uf if uf else None)

    return templates.TemplateResponse("busca.html", {
        "request": request,
        "leads": leads,
        "total": total,
        "pagina": pagina,
        "total_paginas": total_paginas,
        "por_pagina": por_pagina,
        "filtros": filtros,
        "ufs": ufs,
        "cidades": cidades_list,
        "pipeline_status": PIPELINE_STATUS,
        "pipeline_labels": PIPELINE_LABELS,
        "segmentos": SEGMENTOS,
        "segmento_labels": SEGMENTO_LABELS,
        "pagina_ativa": "busca",
    })


@app.get("/api/cidades")
async def api_cidades(uf: str = ""):
    if not uf:
        return []
    return listar_cidades_disponiveis(uf)


# ============================================================
# FICHA DO LEAD
# ============================================================

@app.get("/lead/{lead_id}", response_class=HTMLResponse)
async def ficha_lead(request: Request, lead_id: int, tab: str = "dados"):
    from crm.scoring import avaliar_qualidade_dados

    lead = obter_lead(lead_id)
    if not lead:
        return HTMLResponse("<h1>Lead não encontrado</h1>", status_code=404)

    interacoes = obter_interacoes_lead(lead_id)
    socios = obter_socios_lead(lead_id)

    # Qualidade de dados para tab Ações
    cidade = lead.get("cidade") or ""
    uf = lead.get("uf") or ""
    delivery_ok = cidade_tem_delivery_verificado(cidade, uf) if cidade and uf else False
    qualidade = avaliar_qualidade_dados(lead, delivery_ok)

    # Template recomendado baseado na qualidade
    if qualidade["tem_maps"]:
        template_recomendado = "primeiro_contato"
    else:
        template_recomendado = "primeiro_contato_basico"

    return templates.TemplateResponse("ficha.html", {
        "request": request,
        "lead": lead,
        "interacoes": interacoes,
        "socios": socios,
        "tab": tab,
        "qualidade": qualidade,
        "template_recomendado": template_recomendado,
        "pipeline_status": PIPELINE_STATUS,
        "pipeline_labels": PIPELINE_LABELS,
        "tipos_interacao": TIPOS_INTERACAO,
        "canais": CANAIS,
        "resultados_interacao": RESULTADOS_INTERACAO,
        "pagina_ativa": "lead",
    })


@app.post("/api/lead/{lead_id}/status")
async def api_status(lead_id: int, status: str = Form(...), motivo_perda: str = Form("")):
    atualizar_status_pipeline(lead_id, status, motivo_perda if motivo_perda else None)
    return RedirectResponse(f"/lead/{lead_id}?tab=pipeline", status_code=303)


@app.post("/api/lead/{lead_id}/followup")
async def api_followup(lead_id: int, data: str = Form(...)):
    agendar_followup(lead_id, data)
    return RedirectResponse(f"/lead/{lead_id}?tab=pipeline", status_code=303)


@app.post("/api/lead/{lead_id}/interacao")
async def api_interacao(
    lead_id: int,
    tipo: str = Form(...), canal: str = Form(""),
    conteudo: str = Form(""), resultado: str = Form(""),
):
    registrar_interacao(lead_id, tipo, canal, conteudo, resultado)
    return RedirectResponse(f"/lead/{lead_id}?tab=timeline", status_code=303)


@app.post("/api/lead/{lead_id}/notas")
async def api_notas(lead_id: int, notas: str = Form("")):
    atualizar_notas(lead_id, notas)
    return RedirectResponse(f"/lead/{lead_id}?tab=pipeline", status_code=303)


# ============================================================
# PIPELINE KANBAN
# ============================================================

@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline(request: Request):
    contagens = contagem_pipeline()
    colunas = []
    for status in PIPELINE_STATUS:
        leads = leads_por_pipeline(status, limite=20)
        colunas.append({
            "status": status,
            "label": PIPELINE_LABELS.get(status, status),
            "total": contagens.get(status, 0),
            "leads": leads,
        })

    return templates.TemplateResponse("pipeline.html", {
        "request": request,
        "colunas": colunas,
        "pagina_ativa": "pipeline",
    })


# ============================================================
# EMAIL TEMPLATES
# ============================================================

@app.get("/email/templates", response_class=HTMLResponse)
async def email_templates_page(request: Request):
    tpls = listar_email_templates()
    return templates.TemplateResponse("email_templates.html", {
        "request": request,
        "templates": tpls,
        "pagina_ativa": "email_templates",
    })


@app.post("/api/email/templates")
async def api_criar_template(
    nome: str = Form(...), assunto: str = Form(...),
    corpo_html: str = Form(...), segmento_alvo: str = Form(""),
):
    criar_email_template(nome, assunto, corpo_html, segmento_alvo or None)
    return RedirectResponse("/email/templates", status_code=303)


@app.post("/api/email/templates/{template_id}/deletar")
async def api_deletar_template(template_id: int):
    deletar_email_template(template_id)
    return RedirectResponse("/email/templates", status_code=303)


@app.get("/email/templates/{template_id}/editar", response_class=HTMLResponse)
async def editar_template_page(request: Request, template_id: int):
    tpl = obter_email_template(template_id)
    if not tpl:
        return HTMLResponse("<h1>Template não encontrado</h1>", status_code=404)
    return templates.TemplateResponse("email_template_editar.html", {
        "request": request,
        "template": tpl,
        "pagina_ativa": "email_templates",
    })


@app.post("/api/email/templates/{template_id}/editar")
async def api_atualizar_template(
    template_id: int,
    nome: str = Form(...), assunto: str = Form(...),
    corpo_html: str = Form(...), segmento_alvo: str = Form(""),
):
    atualizar_email_template(template_id, nome, assunto, corpo_html, segmento_alvo or None)
    return RedirectResponse("/email/templates", status_code=303)


# ============================================================
# CAMPANHAS DE EMAIL
# ============================================================

@app.get("/email/campanhas", response_class=HTMLResponse)
async def campanhas_page(request: Request):
    camps = listar_campanhas()
    tpls = listar_email_templates()
    return templates.TemplateResponse("email_campanhas.html", {
        "request": request,
        "campanhas": camps,
        "templates": tpls,
        "pagina_ativa": "email_campanhas",
    })


@app.post("/api/email/campanhas")
async def api_criar_campanha(
    nome: str = Form(...), template_id: int = Form(...),
    filtro_uf: str = Form(""), filtro_segmento: str = Form(""),
):
    filtros = {}
    if filtro_uf:
        filtros["uf"] = filtro_uf
    if filtro_segmento:
        filtros["segmento"] = filtro_segmento

    criar_campanha(nome, template_id, filtros if filtros else None)
    return RedirectResponse("/email/campanhas", status_code=303)


@app.post("/api/email/campanhas/{campanha_id}/enviar")
async def api_enviar_campanha(campanha_id: int, background_tasks: BackgroundTasks):
    from crm.email_service import enviar_campanha

    campanha = obter_campanha(campanha_id)
    if not campanha:
        return JSONResponse({"erro": "Campanha não encontrada"}, status_code=404)

    filtros = campanha.get("filtros_json") or {}
    if isinstance(filtros, str):
        filtros = json.loads(filtros)

    background_tasks.add_task(
        enviar_campanha, campanha_id, filtros, campanha["template_id"]
    )
    return RedirectResponse("/email/campanhas", status_code=303)


# ============================================================
# SEQUÊNCIAS DE EMAIL
# ============================================================

@app.get("/email/sequencias", response_class=HTMLResponse)
async def sequencias_page(request: Request):
    seqs = listar_sequencias()
    return templates.TemplateResponse("email_sequencias.html", {
        "request": request,
        "sequencias": seqs,
        "pagina_ativa": "email_sequencias",
    })


@app.post("/api/email/sequencias")
async def api_criar_sequencia(nome: str = Form(...), descricao: str = Form("")):
    criar_sequencia(nome, descricao or None)
    return RedirectResponse("/email/sequencias", status_code=303)


@app.post("/api/email/sequencias/{sequencia_id}/etapa")
async def api_adicionar_etapa(
    sequencia_id: int,
    template_id: int = Form(...),
    dias_espera: int = Form(1),
    condicao: str = Form("sempre"),
):
    adicionar_etapa_sequencia(sequencia_id, template_id, dias_espera, condicao)
    return RedirectResponse(f"/email/sequencias/{sequencia_id}", status_code=303)


@app.post("/api/email/sequencias/{sequencia_id}/adicionar-leads")
async def api_inscrever_leads(sequencia_id: int, lead_ids: str = Form(...)):
    ids = [int(x.strip()) for x in lead_ids.split(",") if x.strip().isdigit()]
    if ids:
        inscrever_leads_sequencia(ids, sequencia_id)
    return RedirectResponse(f"/email/sequencias/{sequencia_id}", status_code=303)


# ============================================================
# WHATSAPP
# ============================================================

@app.get("/whatsapp", response_class=HTMLResponse)
async def whatsapp_page(request: Request):
    from crm.whatsapp_service import listar_templates_whatsapp
    wa_templates = listar_templates_whatsapp()
    return templates.TemplateResponse("whatsapp.html", {
        "request": request,
        "templates_wa": wa_templates,
        "pagina_ativa": "whatsapp",
    })


@app.get("/api/whatsapp/gerar")
async def api_gerar_whatsapp(
    lead_id: int, template: str = "primeiro_contato",
    tel_proprietario: bool = False,
):
    from crm.whatsapp_service import gerar_link_whatsapp
    resultado = gerar_link_whatsapp(lead_id, template, tel_proprietario)
    if resultado.get("erro") and resultado.get("template_sugerido"):
        return JSONResponse(resultado, status_code=422)
    if resultado.get("erro"):
        return JSONResponse(resultado, status_code=400)
    return JSONResponse(resultado)


@app.get("/whatsapp/enviar/{lead_id}")
async def whatsapp_enviar(lead_id: int, template: str = "primeiro_contato", tel: str = ""):
    from crm.whatsapp_service import gerar_link_whatsapp
    usar_prop = tel == "proprietario"
    resultado = gerar_link_whatsapp(lead_id, template, usar_prop)
    if resultado.get("link"):
        # Registrar interação
        registrar_interacao(lead_id, "whatsapp", "whatsapp",
                           f"WhatsApp enviado ({resultado.get('template_nome', '')})", "")
        return RedirectResponse(resultado["link"], status_code=303)
    return JSONResponse(resultado, status_code=400)


# ============================================================
# WEBHOOK RESEND
# ============================================================

@app.post("/webhooks/resend")
async def webhook_resend(request: Request):
    """Webhook Resend — outbound (opened/clicked/bounced) + inbound (email.received)."""
    from crm.email_service import processar_webhook_resend, processar_email_inbound
    payload = await request.json()
    event_type = payload.get("type", "")

    # Inbound email
    if event_type == "email.received":
        resultado = processar_email_inbound(payload)
        return JSONResponse(resultado)

    # Outbound tracking (opened, clicked, bounced, complained)
    resultado = processar_webhook_resend(payload)
    return JSONResponse(resultado)


# ============================================================
# EMAIL INBOX — Caixa de Entrada
# ============================================================

@app.get("/emails", response_class=HTMLResponse)
async def emails_inbox_page(request: Request,
                            categoria: str = "",
                            busca: str = "",
                            pagina: int = 1):
    """Página da caixa de entrada de emails."""
    limite = 30
    offset = (pagina - 1) * limite

    threads = listar_email_threads(
        categoria=categoria or None,
        busca=busca or None,
        limite=limite,
        offset=offset,
    )
    contadores = contar_threads_por_categoria()
    from crm.database import email_quota_resend
    quota = email_quota_resend()

    return templates.TemplateResponse("emails_inbox.html", {
        "request": request,
        "pagina_ativa": "emails",
        "threads": threads,
        "contadores": contadores,
        "categoria_ativa": categoria,
        "busca": busca,
        "pagina": pagina,
        "quota": quota,
    })


@app.get("/api/emails/threads")
async def api_listar_threads(categoria: str = "", lido: str = "",
                              busca: str = "",
                              limite: int = 50, offset: int = 0):
    """API: listar threads de email."""
    threads = listar_email_threads(
        categoria=categoria or None,
        lido=True if lido == "true" else (False if lido == "false" else None),
        busca=busca or None,
        limite=limite,
        offset=offset,
    )
    contadores = contar_threads_por_categoria()
    return JSONResponse(json.loads(json.dumps({
        "threads": threads,
        "contadores": contadores,
    }, default=str)))


@app.get("/api/emails/thread/{thread_id}")
async def api_obter_thread(thread_id: int):
    """API: obter thread com mensagens."""
    thread = obter_email_thread(thread_id)
    if not thread:
        return JSONResponse({"erro": "Thread não encontrada"}, status_code=404)
    # Marcar como lida
    marcar_thread_lida(thread_id)
    return JSONResponse(json.loads(json.dumps(thread, default=str)))


@app.post("/api/emails/thread/{thread_id}/responder")
async def api_responder_email(thread_id: int, request: Request):
    """Responder email de uma thread."""
    from crm.email_service import responder_email
    body = await request.json()
    corpo_html = body.get("corpo_html", "").strip()
    corpo_texto = body.get("corpo_texto", "").strip()

    if not corpo_html and not corpo_texto:
        return JSONResponse({"erro": "Corpo da resposta vazio"}, status_code=400)

    # Se só tem texto, converter para HTML básico
    if not corpo_html and corpo_texto:
        corpo_html = corpo_texto.replace("\n", "<br>")

    resultado = responder_email(thread_id, corpo_html, corpo_texto)
    if resultado.get("erro"):
        return JSONResponse(resultado, status_code=400)
    return JSONResponse(resultado)


@app.post("/api/emails/thread/{thread_id}/lido")
async def api_marcar_lido(thread_id: int):
    """Marcar thread como lida."""
    marcar_thread_lida(thread_id)
    return JSONResponse({"ok": True})


@app.post("/api/emails/thread/{thread_id}/starred")
async def api_toggle_starred(thread_id: int, request: Request):
    """Toggle favorito da thread."""
    body = await request.json()
    starred = body.get("starred", True)
    marcar_thread_starred(thread_id, starred)
    return JSONResponse({"ok": True})


@app.post("/api/emails/thread/{thread_id}/arquivar")
async def api_arquivar_thread(thread_id: int):
    """Arquivar thread."""
    arquivar_thread(thread_id)
    return JSONResponse({"ok": True})


@app.post("/api/emails/thread/{thread_id}/categorizar")
async def api_categorizar_thread(thread_id: int, request: Request):
    """Alterar categoria de uma thread."""
    body = await request.json()
    categoria = body.get("categoria", "")
    if categorizar_thread(thread_id, categoria):
        return JSONResponse({"ok": True})
    return JSONResponse({"erro": "Categoria inválida"}, status_code=400)


@app.get("/api/emails/contadores")
async def api_contadores_email():
    """Contadores por categoria (para badges no sidebar)."""
    return JSONResponse(contar_threads_por_categoria())


# ============================================================
# SCORING (API)
# ============================================================

@app.get("/api/scoring/recalcular")
async def api_recalcular_scores(background_tasks: BackgroundTasks):
    from crm.scoring import calcular_scores_todos
    background_tasks.add_task(calcular_scores_todos)
    return RedirectResponse("/", status_code=303)


@app.post("/api/wa/migrar-numero")
async def api_migrar_numero(
    request: Request,
    limite: int = Query(default=50),
    key: str = Query(default=""),
):
    """Roda migração de conversas para novo número em background.
    Protegido por chave secreta na query string."""
    secret = os.environ.get("CRM_ADMIN_KEY", "derekh_migra_2026")
    if key != secret:
        return JSONResponse({"erro": "Chave inválida"}, status_code=403)

    from crm.wa_sales_bot import migrar_conversas_novo_numero
    import threading

    def _run_migration():
        try:
            result = migrar_conversas_novo_numero(limite=limite)
            log.info(f"Migração background concluída: {result}")
        except Exception as e:
            log.error(f"Erro migração background: {e}")

    t = threading.Thread(target=_run_migration, daemon=True)
    t.start()
    return JSONResponse({"status": "migração iniciada em background", "limite": limite})


# ============================================================
# EMAIL: ENVIAR PARA LEAD
# ============================================================

@app.get("/email/enviar/{lead_id}", response_class=HTMLResponse)
async def email_enviar_page(request: Request, lead_id: int):
    lead = obter_lead(lead_id)
    if not lead:
        return HTMLResponse("<h1>Lead não encontrado</h1>", status_code=404)
    tpls = listar_email_templates()
    return templates.TemplateResponse("email_enviar.html", {
        "request": request,
        "lead": lead,
        "templates": tpls,
        "pagina_ativa": "lead",
    })


@app.post("/api/email/enviar/{lead_id}")
async def api_enviar_email_lead(lead_id: int, template_id: int = Form(...)):
    from crm.email_service import enviar_email
    resultado = enviar_email(lead_id, template_id)
    if resultado.get("sucesso"):
        return RedirectResponse(f"/lead/{lead_id}?tab=timeline", status_code=303)
    return JSONResponse(resultado, status_code=400)


# ============================================================
# EMAIL: PREVIEW
# ============================================================

@app.get("/api/email/preview")
async def api_preview_email(template_id: int, lead_id: int):
    from crm.email_service import preview_template
    return JSONResponse(preview_template(template_id, lead_id))


# ============================================================
# CONFIGURAÇÕES
# ============================================================

@app.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes_page(request: Request, salvo: str = ""):
    configs = obter_configuracoes_todas()
    return templates.TemplateResponse("configuracoes.html", {
        "request": request,
        "configs": configs,
        "salvo": salvo == "1",
        "pagina_ativa": "configuracoes",
    })


@app.post("/api/configuracoes")
async def api_salvar_configuracoes(
    nome_usuario: str = Form(""),
    empresa: str = Form(""),
    cargo: str = Form(""),
    telefone_usuario: str = Form(""),
    email_usuario: str = Form(""),
):
    for chave, valor in [
        ("nome_usuario", nome_usuario),
        ("empresa", empresa),
        ("cargo", cargo),
        ("telefone_usuario", telefone_usuario),
        ("email_usuario", email_usuario),
    ]:
        salvar_configuracao(chave, valor.strip())
    return RedirectResponse("/configuracoes?salvo=1", status_code=303)


# ============================================================
# SCANNER - VARREDURA DE LEADS
# ============================================================

@app.get("/api/health/db")
async def health_db():
    """Health check do PostgreSQL (scanner)."""
    from db_pg import _pool, get_conn
    if _pool is None:
        return JSONResponse({"status": "error", "msg": "Pool PostgreSQL não inicializado"}, status_code=503)
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 as ok")
            row = cur.fetchone()
            return JSONResponse({"status": "ok", "pool_size": _pool.minconn})
    except Exception as e:
        return JSONResponse({"status": "error", "msg": str(e)}, status_code=503)


@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page(request: Request):
    """Pagina principal do scanner de leads."""
    try:
        init_pg()
    except Exception as e:
        print(f"[SCANNER] init_pg falhou: {e}")

    try:
        cidades = stats_cidades_scanner()
    except Exception as e:
        print(f"[SCANNER] stats_cidades_scanner falhou: {e}")
        cidades = []

    try:
        jobs = listar_scan_jobs(20)
    except Exception as e:
        print(f"[SCANNER] listar_scan_jobs falhou: {e}")
        jobs = []

    try:
        scan_ativo = existe_scan_ativo()
    except Exception as e:
        print(f"[SCANNER] existe_scan_ativo falhou: {e}")
        scan_ativo = None

    return templates.TemplateResponse("scanner.html", {
        "request": request,
        "cidades": cidades,
        "jobs": jobs,
        "scan_ativo": scan_ativo,
        "cidades_json": json.dumps(cidades, default=str),
        "pagina_ativa": "scanner",
    })


@app.post("/api/scan/start")
async def api_start_scan(
    cidades: str = Form(...),
    etapas: str = Form(...),
    headless: str = Form("on"),
):
    """Inicia um novo scan."""
    try:
        init_pg()
    except Exception as e:
        return JSONResponse(
            {"erro": f"PostgreSQL não disponível: {e}. Verifique DATABASE_URL."},
            status_code=503
        )

    # Verificar pool
    from db_pg import _pool
    if _pool is None:
        return JSONResponse(
            {"erro": "Pool PostgreSQL não inicializado. Verifique DATABASE_URL e conectividade."},
            status_code=503
        )

    # Parse cidades: "SAO PAULO|SP,RIO DE JANEIRO|RJ"
    cidades_list = []
    for c in cidades.split(","):
        c = c.strip()
        if "|" in c:
            cidade, uf = c.split("|", 1)
            cidades_list.append([cidade.strip(), uf.strip()])

    if not cidades_list:
        return JSONResponse({"erro": "Nenhuma cidade selecionada"}, status_code=400)

    # Parse etapas: "ifood,rappi,99food,maps"
    etapas_list = [e.strip() for e in etapas.split(",") if e.strip()]
    if not etapas_list:
        return JSONResponse({"erro": "Nenhuma etapa selecionada"}, status_code=400)

    # Verificar scan ativo
    ativo = existe_scan_ativo()
    if ativo:
        return JSONResponse(
            {"erro": f"Ja existe scan ativo (#{ativo['id']})"},
            status_code=409
        )

    is_headless = headless == "on"

    # Criar job
    job_id = criar_scan_job(cidades_list, etapas_list, is_headless)
    print(f"[SCANNER] Job #{job_id} criado: {len(cidades_list)} cidades, etapas={etapas_list}")

    # Scan será executado pelo scanner_agent.py local (polling PostgreSQL)
    # Job fica como 'pendente' até o agent capturar

    return RedirectResponse(f"/scanner/job/{job_id}", status_code=303)


@app.get("/scanner/job/{job_id}", response_class=HTMLResponse)
async def scanner_job_page(request: Request, job_id: int):
    """Pagina de detalhe/logs de um scan job."""
    init_pg()
    job = obter_scan_job(job_id)
    if not job:
        return HTMLResponse("<h1>Scan nao encontrado</h1>", status_code=404)
    logs = obter_scan_logs(job_id, offset=0, limite=500)

    return templates.TemplateResponse("scan_detail.html", {
        "request": request,
        "job": job,
        "logs": logs,
        "job_json": json.dumps(job, default=str),
        "pagina_ativa": "scanner",
    })


@app.get("/api/scan/{job_id}")
async def api_scan_status(job_id: int):
    """Status atual do scan (para polling)."""
    init_pg()
    job = obter_scan_job(job_id)
    if not job:
        return JSONResponse({"erro": "nao encontrado"}, status_code=404)
    return JSONResponse({
        "id": job["id"],
        "status": job["status"],
        "cidade_atual": job.get("cidade_atual"),
        "etapa_atual": job.get("etapa_atual"),
        "processados": job.get("processados", 0),
        "encontrados": job.get("encontrados", 0),
        "erros": job.get("erros", 0),
        "progresso": job.get("progresso"),
    })


@app.get("/api/scan/{job_id}/logs")
async def api_scan_logs(job_id: int, after: int = 0):
    """Logs do scan (para polling, envia apenas novos)."""
    init_pg()
    logs = obter_scan_logs(job_id, offset=after, limite=100)
    return JSONResponse(logs)


@app.post("/api/scan/{job_id}/cancel")
async def api_cancel_scan(job_id: int):
    """Cancela scan — marca como 'cancelando' para o agent local detectar."""
    job = obter_scan_job(job_id)
    if not job:
        return JSONResponse({"erro": "Job não encontrado"}, status_code=404)
    if job["status"] in ("pendente", "executando"):
        atualizar_scan_job(job_id, status="cancelando")
        return JSONResponse({"ok": True, "msg": "Cancelamento solicitado"})
    return JSONResponse({"ok": True, "msg": "Job já finalizado"})


# ============================================================
# TRACKING — PIXEL, CLIQUES, UNSUBSCRIBE (Fase 7)
# ============================================================

# Pixel GIF 1x1 transparente (43 bytes)
import base64
PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@app.get("/tracking/pixel/{tracking_id}")
async def tracking_pixel(tracking_id: str):
    """Pixel de abertura de email. Retorna GIF 1x1 e marca como aberto."""
    from fastapi.responses import Response
    try:
        marcar_email_aberto(tracking_id)
        # P4.1: Event scoring — email aberto
        email_reg = buscar_email_por_tracking(tracking_id)
        if email_reg and email_reg.get("lead_id"):
            from crm.scoring import atualizar_score_evento
            atualizar_score_evento(email_reg["lead_id"], "email_aberto")
    except Exception:
        pass  # Não falhar — pixel deve sempre retornar imagem
    return Response(content=PIXEL_GIF, media_type="image/gif",
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/tracking/click/{tracking_id}/{tipo}")
async def tracking_click(tracking_id: str, tipo: str, url: str = ""):
    """Registra clique e redireciona para URL destino."""
    try:
        marcar_email_clique(tracking_id, tipo)
        # P4.1: Event scoring — email clicado
        email_reg = buscar_email_por_tracking(tracking_id)
        if email_reg and email_reg.get("lead_id"):
            from crm.scoring import atualizar_score_evento
            atualizar_score_evento(email_reg["lead_id"], "email_clicado")
    except Exception:
        pass
    destino = url or "https://derekhfood.com.br"
    return RedirectResponse(url=destino, status_code=302)


@app.get("/tracking/unsub/{tracking_id}", response_class=HTMLResponse)
async def tracking_unsub(tracking_id: str, request: Request):
    """Processa opt-out de email. Mostra página de confirmação."""
    email_reg = buscar_email_por_tracking(tracking_id)
    cancelado = False
    if email_reg:
        try:
            marcar_email_clique(tracking_id, "unsub")
            opt_out_lead(email_reg["lead_id"], "email")
            cancelado = True
        except Exception:
            pass

    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cancelar inscrição — Derekh Food</title>
    <style>body{{font-family:system-ui,-apple-system,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f9fafb;color:#374151;}}
    .card{{background:#fff;border-radius:12px;padding:40px;max-width:440px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);}}
    h2{{color:#111827;margin-bottom:8px;}} p{{line-height:1.6;color:#6b7280;}} .ok{{color:#10b981;font-size:48px;margin-bottom:16px;}}</style></head>
    <body><div class="card">
    <div class="ok">{'✓' if cancelado else '⚠'}</div>
    <h2>{'Inscrição cancelada' if cancelado else 'Link inválido'}</h2>
    <p>{'Você não receberá mais emails da Derekh Food. Se mudar de ideia, entre em contato.' if cancelado else 'Este link de cancelamento não é válido ou já foi utilizado.'}</p>
    </div></body></html>
    """
    return HTMLResponse(html)


# ============================================================
# OUTREACH — STATS API (Fase 7)
# ============================================================

@app.get("/api/outreach/stats")
async def api_outreach_stats(dias: int = 7):
    """Stats de outreach (emails enviados, abertos, clicados, bounce)."""
    from crm.database import email_quota_resend
    stats = stats_outreach(dias)
    stats["emails_hoje"] = emails_enviados_hoje()
    stats["max_email_dia"] = int(obter_configuracoes_todas().get("outreach_max_email_dia", "20"))
    stats["quota"] = email_quota_resend()
    return JSONResponse(stats)


@app.get("/api/emails/quota")
async def api_email_quota():
    """Quota Resend: enviados hoje/mês, limites, restante."""
    from crm.database import email_quota_resend
    return JSONResponse(email_quota_resend())


@app.get("/api/outreach/pendentes")
async def api_outreach_pendentes():
    """Lista ações de outreach pendentes."""
    pendentes = listar_outreach_pendentes(50)
    return JSONResponse(json.loads(json.dumps(pendentes, default=str)))


@app.get("/api/outreach/futuras")
async def api_outreach_futuras():
    """Lista próximas ações agendadas."""
    futuras = listar_outreach_futuras(50)
    return JSONResponse(json.loads(json.dumps(futuras, default=str)))


@app.post("/api/outreach/opt-out/{lead_id}")
async def api_outreach_opt_out(lead_id: int, canal: str = "email"):
    """Opt-out de um lead (cancela ações pendentes)."""
    ok = opt_out_lead(lead_id, canal)
    if ok:
        return JSONResponse({"ok": True, "msg": f"Opt-out {canal} registrado para lead {lead_id}"})
    return JSONResponse({"ok": False, "msg": "Canal inválido"}, status_code=400)


@app.post("/api/outreach/cancelar/{lead_id}")
async def api_outreach_cancelar(lead_id: int):
    """Cancela todas ações pendentes de um lead."""
    count = cancelar_outreach_lead(lead_id)
    return JSONResponse({"ok": True, "canceladas": count})


@app.post("/api/outreach/importar")
async def api_outreach_importar(request: Request):
    """Importa leads para outreach e cria sequências."""
    from crm.outreach_engine import importar_leads_para_outreach
    body = await request.json()
    cidade = body.get("cidade", "")
    uf = body.get("uf", "")
    score_min = int(body.get("score_min", 30))
    limite = int(body.get("limite", 50))
    leads = importar_leads_para_outreach(cidade or None, uf or None, score_min, limite)
    return JSONResponse({
        "ok": True,
        "importados": len(leads),
        "leads": [{"id": l["id"], "nome": l.get("nome_fantasia") or l.get("razao_social"),
                    "tier": l["tier"], "acoes": l["acoes_criadas"]} for l in leads]
    })


@app.post("/api/outreach/iniciar/{lead_id}")
async def api_outreach_iniciar(lead_id: int):
    """Cria sequência de outreach para 1 lead específico."""
    from crm.outreach_engine import criar_sequencia_lead
    from crm.scoring import calcular_tier
    lead = obter_lead(lead_id)
    if not lead:
        return JSONResponse({"ok": False, "msg": "Lead não encontrado"}, status_code=404)
    score = lead.get("lead_score", 0)
    tier = calcular_tier(score)
    atualizar_tier_lead(lead_id, tier)
    acoes = criar_sequencia_lead(lead_id, tier, score)
    return JSONResponse({"ok": True, "tier": tier, "acoes_criadas": len(acoes)})


@app.post("/api/outreach/forcar-execucao")
async def api_outreach_forcar():
    """Força execução imediata do worker de outreach."""
    from crm.outreach_engine import executar_acoes_pendentes
    stats = executar_acoes_pendentes()
    return JSONResponse({"ok": True, "stats": stats})


@app.get("/outreach", response_class=HTMLResponse)
async def outreach_dashboard(request: Request):
    """Dashboard de outreach com stats, funil e ações pendentes."""
    from crm.models import TIER_LABELS, TIER_CORES, ACOES_OUTREACH_LABELS
    stats = stats_outreach(7)
    stats["emails_hoje"] = emails_enviados_hoje()
    configs = obter_configuracoes_todas()
    stats["max_email_dia"] = int(configs.get("outreach_max_email_dia", "20"))
    stats["outreach_ativo"] = configs.get("outreach_ativo", "false") == "true"

    pendentes = listar_outreach_pendentes(20)
    futuras = listar_outreach_futuras(20)

    # Distribuição por tier
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT tier, COUNT(*) as total FROM leads
            WHERE tier IS NOT NULL AND tier != 'cold'
            GROUP BY tier ORDER BY total DESC
        """)
        dist_tier = [dict(r) for r in cur.fetchall()]

    from crm.database import email_quota_resend
    quota = email_quota_resend()

    return templates.TemplateResponse("outreach_dashboard.html", {
        "request": request,
        "stats": stats,
        "pendentes": pendentes,
        "futuras": futuras,
        "dist_tier": dist_tier,
        "quota": quota,
        "TIER_LABELS": TIER_LABELS,
        "TIER_CORES": TIER_CORES,
        "ACOES_OUTREACH_LABELS": ACOES_OUTREACH_LABELS,
    })


# ============================================================
# WHATSAPP SALES BOT (Fase 7 - Micro-Fase 3)
# ============================================================

@app.post("/wa-sales/enviar/{lead_id}")
async def wa_sales_enviar(lead_id: int, request: Request):
    """Envia mensagem WA manual para um lead."""
    from crm.wa_sales_bot import enviar_mensagem_wa
    body = await request.json()
    texto = body.get("texto", "")
    tom = body.get("tom", "informal")
    if not texto:
        return JSONResponse({"ok": False, "msg": "Texto vazio"}, status_code=400)
    result = enviar_mensagem_wa(lead_id, texto, tom)
    if result.get("sucesso"):
        return JSONResponse({"ok": True, "conversa_id": result["conversa_id"]})
    return JSONResponse({"ok": False, "msg": result.get("erro")}, status_code=400)


@app.post("/wa-sales/audio/{lead_id}")
async def wa_sales_audio(lead_id: int):
    """Envia áudio TTS personalizado para um lead (Fish Audio)."""
    from crm.wa_sales_bot import enviar_audio_wa
    result = enviar_audio_wa(lead_id)
    if result.get("sucesso"):
        return JSONResponse({"ok": True, "conversa_id": result["conversa_id"]})
    return JSONResponse({"ok": False, "msg": result.get("erro")}, status_code=400)


@app.get("/wa-sales/webhook")
async def wa_sales_webhook_verify(request: Request):
    """Webhook verification (Meta Cloud API challenge)."""
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "derekh_wa_verify_2026")
    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and token == verify_token:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)


# Deduplicação: cache de message IDs processados (TTL ~5 min)
_webhook_msg_ids = {}
_WEBHOOK_DEDUP_MAX = 500

# Números dos próprios bots — ignorar para evitar loop cross-instance
# (quando bot A envia para número de bot B, bot B recebe como incoming e responderia → loop infinito)
_BOT_PHONE_NUMBERS = set()


def _init_bot_phone_numbers():
    """Carrega números dos bots (Evolution legado + Meta Cloud API)."""
    import re
    nums = [
        "351961330536",   # Ana +351 961 330 536 (Meta Cloud API principal)
    ]
    for n in nums:
        clean = re.sub(r"\D", "", n)
        if clean:
            _BOT_PHONE_NUMBERS.add(clean)


_init_bot_phone_numbers()


@app.post("/wa-sales/webhook")
async def wa_sales_webhook(request: Request):
    """Webhook WhatsApp — suporta Evolution API + Meta Cloud API."""
    from crm.wa_sales_bot import processar_resposta_wa, verificar_webhook_meta
    import time

    raw_body = await request.body()
    body = json.loads(raw_body)

    # DEBUG: Log completo de TODOS os webhooks recebidos
    obj_type = body.get("object", "")
    event = body.get("event", "")
    if obj_type == "whatsapp_business_account":
        for _entry in body.get("entry", []):
            for _change in _entry.get("changes", []):
                _field = _change.get("field", "?")
                _val = _change.get("value", {})
                _has_msgs = "messages" in _val
                _has_statuses = "statuses" in _val
                _contacts = _val.get("contacts", [])
                print(f"[WA-WEBHOOK-DEBUG] field={_field} has_messages={_has_msgs} has_statuses={_has_statuses} contacts={_contacts}")
                if _has_msgs:
                    for _m in _val["messages"]:
                        print(f"[WA-WEBHOOK-DEBUG] MSG: from={_m.get('from')} type={_m.get('type')} id={_m.get('id')}")
                if _has_statuses:
                    for _s in _val["statuses"]:
                        print(f"[WA-WEBHOOK-DEBUG] STATUS: id={_s.get('id')} status={_s.get('status')} recipient={_s.get('recipient_id')}")
    else:
        print(f"[WA-WEBHOOK-DEBUG] event={event} object={obj_type} keys={list(body.keys())[:5]}")

    # --- EVOLUTION API FORMAT ---
    if event == "messages.upsert":
        data = body.get("data", {})
        key = data.get("key", {})

        # Extrair nome da instância (para responder pelo mesmo número)
        instance = body.get("instance", "")

        # Ignorar eventos de instâncias que NÃO pertencem ao CRM
        # (ex: derekh-whatsapp é do bot restaurante, não do CRM)
        _CRM_INSTANCES = os.environ.get("EVOLUTION_CRM_INSTANCES", "derekh-inbound").split(",")
        if instance and instance not in _CRM_INSTANCES:
            print(f"[WA-WEBHOOK] IGNORANDO evento de instância {instance} (não é do CRM)")
            return JSONResponse({"status": "ok"})

        # Ignorar mensagens enviadas por nós (fromMe=true)
        if key.get("fromMe"):
            return JSONResponse({"status": "ok"})

        # Deduplicação por message ID
        msg_id = key.get("id", "")
        if msg_id:
            now = time.time()
            if msg_id in _webhook_msg_ids:
                return JSONResponse({"status": "ok"})  # Já processado
            _webhook_msg_ids[msg_id] = now
            # Limpar cache antigo
            if len(_webhook_msg_ids) > _WEBHOOK_DEDUP_MAX:
                cutoff = now - 300  # 5 min
                _webhook_msg_ids.clear()

        # Extrair número (remoteJid: "5511999999999@s.whatsapp.net")
        jid = key.get("remoteJid", "")
        numero = jid.split("@")[0] if "@" in jid else ""

        # Ignorar grupos
        if "@g.us" in jid:
            return JSONResponse({"status": "ok"})

        # Ignorar mensagens vindas dos próprios números do bot (evita loop cross-instance)
        if numero in _BOT_PHONE_NUMBERS:
            print(f"[WA-WEBHOOK] [{instance}] IGNORANDO msg do próprio bot: {numero}")
            return JSONResponse({"status": "ok"})

        # Extrair texto da mensagem
        msg = data.get("message", {})
        texto = (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or ""
        )

        # Detectar áudio
        audio_msg = msg.get("audioMessage", {})
        msg_key_id = key.get("id", "")

        if numero and audio_msg and msg_key_id:
            # Verificar toggle STT
            from crm.database import obter_configuracao
            stt_ativo = (obter_configuracao("audio_stt_ativo") or "true").lower() == "true"

            if stt_ativo:
                print(f"[WA-WEBHOOK] [{instance}] {numero} -> [ÁUDIO] (transcrever)")
                from crm.wa_sales_bot import baixar_audio_evolution, transcrever_audio
                import time as _t

                # Baixar áudio via Evolution
                audio_data = baixar_audio_evolution(msg_key_id, instance=instance)
                if audio_data.get("base64"):
                    # Transcrever com Groq Whisper
                    duracao = audio_msg.get("seconds", 0)
                    transcricao = transcrever_audio(audio_data["base64"], duracao)
                    if transcricao.get("texto"):
                        texto = transcricao["texto"]
                        duracao_real = transcricao.get("duracao", duracao)
                        print(f"[WA-WEBHOOK] [{instance}] {numero} -> [ÁUDIO→TEXTO] {texto[:80]}")
                        # Delay proporcional (simular escuta do áudio)
                        from crm.wa_sales_bot import _calcular_delay_audio
                        delay = _calcular_delay_audio(duracao_real)
                        print(f"[WA-WEBHOOK] Delay áudio: {delay:.1f}s (duração {duracao_real}s)")
                        _t.sleep(delay)
                        # Processar como texto transcrito (tipo=audio para reciprocidade)
                        processar_resposta_wa(numero, texto, instance=instance, tipo_msg="audio")
                        return JSONResponse({"status": "ok"})
                    else:
                        print(f"[WA-WEBHOOK] Transcrição falhou: {transcricao.get('erro')}")
                else:
                    print(f"[WA-WEBHOOK] Download áudio falhou: {audio_data.get('erro')}")
            else:
                print(f"[WA-WEBHOOK] [{instance}] {numero} -> [ÁUDIO] STT desativado, ignorando")

            return JSONResponse({"status": "ok"})

        if numero and texto:
            print(f"[WA-WEBHOOK] [{instance}] {numero} -> {texto[:80]}")
            processar_resposta_wa(numero, texto, instance=instance)

        return JSONResponse({"status": "ok"})

    # Ignorar outros eventos Evolution (CONNECTION_UPDATE, presence, etc.)
    if event:
        return JSONResponse({"status": "ok"})

    # --- META CLOUD API FORMAT ---
    # {object: "whatsapp_business_account", entry: [{changes: [{value: {messages: [...]}}]}]}
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature and not verificar_webhook_meta(raw_body, signature):
        return JSONResponse({"erro": "Assinatura inválida"}, status_code=403)

    from crm.wa_sales_bot import (
        _marcar_lida_cloud_api, _enviar_presenca_cloud_api,
        baixar_audio_meta, transcrever_audio, _calcular_delay_audio,
    )
    import time as _t

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                numero = msg.get("from", "")
                msg_id = msg.get("id", "")
                msg_type = msg.get("type", "")

                # Ignorar números do próprio bot
                if numero in _BOT_PHONE_NUMBERS:
                    continue

                # Deduplicação
                if msg_id:
                    now = time.time()
                    if msg_id in _webhook_msg_ids:
                        continue
                    _webhook_msg_ids[msg_id] = now
                    if len(_webhook_msg_ids) > _WEBHOOK_DEDUP_MAX:
                        _webhook_msg_ids.clear()

                # Marcar como lida (ticks azuis) imediatamente
                if msg_id:
                    _marcar_lida_cloud_api(msg_id)

                # Extrair texto por tipo de mensagem
                texto = ""
                tipo_msg = "texto"

                if msg_type == "text":
                    texto = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    texto = (msg.get("interactive", {}).get("button_reply", {}).get("title", "")
                             or msg.get("interactive", {}).get("list_reply", {}).get("title", ""))
                elif msg_type == "audio":
                    # Áudio: baixar via Meta Media API + transcrever STT
                    from crm.database import obter_configuracao
                    stt_ativo = (obter_configuracao("audio_stt_ativo") or "true").lower() == "true"
                    audio_meta = msg.get("audio", {})
                    audio_id = audio_meta.get("id", "")
                    duracao = audio_meta.get("duration", 0) or 0

                    if stt_ativo and audio_id:
                        print(f"[WA-WEBHOOK] [META] {numero} -> [ÁUDIO] (transcrever)")
                        audio_data = baixar_audio_meta(audio_id)
                        if audio_data.get("base64"):
                            transcricao = transcrever_audio(audio_data["base64"], duracao)
                            if transcricao.get("texto"):
                                texto = transcricao["texto"]
                                tipo_msg = "audio"
                                duracao_real = transcricao.get("duracao", duracao)
                                print(f"[WA-WEBHOOK] [META] {numero} -> [ÁUDIO→TEXTO] {texto[:80]}")
                                delay = _calcular_delay_audio(duracao_real)
                                _t.sleep(delay)
                            else:
                                print(f"[WA-WEBHOOK] Transcrição falhou: {transcricao.get('erro')}")
                        else:
                            print(f"[WA-WEBHOOK] Download áudio Meta falhou: {audio_data.get('erro')}")
                    else:
                        print(f"[WA-WEBHOOK] [META] {numero} -> [ÁUDIO] STT desativado, ignorando")
                elif msg_type in ("image", "video", "document", "sticker"):
                    # Mídia não processada — ignorar silenciosamente
                    continue
                elif msg_type == "reaction":
                    continue

                if numero and texto:
                    print(f"[WA-WEBHOOK] [META] {numero} -> {texto[:80]}")
                    # Enviar "digitando..." antes de processar
                    _enviar_presenca_cloud_api(numero)
                    processar_resposta_wa(numero, texto, tipo_msg=tipo_msg)

    return JSONResponse({"status": "ok"})


@app.get("/wa-sales/conversas", response_class=HTMLResponse)
async def wa_sales_conversas(request: Request, status: str = ""):
    """Lista de conversas WhatsApp de vendas."""
    conversas = listar_conversas_wa(status or None, 50)
    wa_stats = stats_wa(7)
    return templates.TemplateResponse("wa_conversas.html", {
        "request": request,
        "conversas": conversas,
        "stats": wa_stats,
        "filtro_status": status,
    })


@app.get("/wa-sales/conversa/{conversa_id}", response_class=HTMLResponse)
async def wa_sales_conversa_detalhe(conversa_id: int, request: Request):
    """Detalhe de uma conversa WA com histórico."""
    conv = obter_conversa_wa(conversa_id)
    if not conv:
        return RedirectResponse("/wa-sales/conversas")
    return templates.TemplateResponse("wa_conversa_detalhe.html", {
        "request": request,
        "conversa": conv,
    })


# ============================================================
# CONTACT VALIDATOR
# ============================================================

@app.post("/api/validar/{lead_id}")
async def api_validar_lead(lead_id: int):
    """Valida contatos de um lead específico."""
    from crm.contact_validator import validar_contatos_lead
    resultado = validar_contatos_lead(lead_id)
    if resultado.get("erro"):
        return JSONResponse(resultado, status_code=404)
    return JSONResponse(resultado)


@app.post("/api/validar/lote")
async def api_validar_lote(
    request: Request,
    background_tasks: BackgroundTasks,
    cidade: str = Query(""), uf: str = Query(""), limite: int = Query(500),
):
    """Valida contatos em lote (background)."""
    from crm.contact_validator import validar_lote
    background_tasks.add_task(
        validar_lote,
        cidade=cidade if cidade else None,
        uf=uf if uf else None,
        limite=limite,
    )
    return JSONResponse({"ok": True, "msg": f"Validação em background iniciada (limite={limite})"})


# ============================================================
# QUIZ DIAGNÓSTICO — INBOUND LANDING PAGE
# ============================================================

@app.post("/api/leads/quiz")
async def api_lead_quiz(request: Request):
    """Recebe dados do quiz diagnóstico da landing page. Rota pública."""
    import re
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "erro": "JSON inválido"}, status_code=400)

    nome = (body.get("nome") or "").strip()
    nome_restaurante = (body.get("nome_restaurante") or "").strip()
    tipo_restaurante = (body.get("tipo_restaurante") or "").strip()
    whatsapp_raw = (body.get("whatsapp") or "").strip()
    email = (body.get("email") or "").strip()
    pedidos_dia = (body.get("pedidos_dia") or "").strip()
    respostas = body.get("respostas", {})
    diagnostico = body.get("diagnostico", {})

    if not whatsapp_raw:
        return JSONResponse({"ok": False, "erro": "WhatsApp obrigatório"}, status_code=400)

    # Normalizar WhatsApp — só dígitos, prefixar 55 se necessário
    whatsapp = re.sub(r"\D", "", whatsapp_raw)
    if len(whatsapp) <= 11:
        whatsapp = "55" + whatsapp

    # Criar lead no CRM
    try:
        lead_id = criar_lead_quiz({
            "nome": nome,
            "nome_restaurante": nome_restaurante,
            "tipo_restaurante": tipo_restaurante,
            "whatsapp": whatsapp,
            "email": email,
            "pedidos_dia": pedidos_dia,
            "respostas": respostas,
            "diagnostico": diagnostico,
        })
        return JSONResponse({"ok": True, "lead_id": lead_id})
    except Exception as e:
        print(f"[QUIZ] Erro ao criar lead: {e}")
        return JSONResponse({"ok": False, "erro": str(e)}, status_code=500)


# ============================================================
# AGENTE AUTÔNOMO (Fase 7 - Micro-Fase 5)
# ============================================================

@app.get("/agente", response_class=HTMLResponse)
async def agente_dashboard(request: Request):
    """Dashboard do agente autônomo."""
    experimentos = listar_experimentos(ativo=True)
    decisoes = listar_decisoes_pendentes()
    ultimo_rel = obter_ultimo_relatorio()
    email_stats = stats_outreach(7)
    wa_stats = stats_wa(7)
    return templates.TemplateResponse("agente_dashboard.html", {
        "request": request,
        "experimentos": experimentos,
        "decisoes": decisoes,
        "relatorio": ultimo_rel,
        "email_stats": email_stats,
        "wa_stats": wa_stats,
    })


@app.post("/api/agente/forcar-ciclo")
async def api_agente_forcar():
    """Força execução do ciclo diário do agente."""
    from crm.agente_autonomo import ciclo_diario
    resultado = ciclo_diario()
    return JSONResponse(json.loads(json.dumps({"ok": True, "resultado": resultado}, default=str)))


@app.post("/api/agente/aprovar/{decisao_id}")
async def api_agente_aprovar(decisao_id: int):
    """Aprova decisão do agente."""
    ok = aprovar_decisao(decisao_id)
    return JSONResponse({"ok": ok})


@app.post("/api/agente/rejeitar/{decisao_id}")
async def api_agente_rejeitar(decisao_id: int):
    """Rejeita decisão do agente."""
    ok = rejeitar_decisao(decisao_id)
    return JSONResponse({"ok": ok})


@app.get("/api/agente/experimentos")
async def api_agente_experimentos():
    """Lista experimentos ativos."""
    exps = listar_experimentos(ativo=True)
    return JSONResponse(json.loads(json.dumps(exps, default=str)))


@app.get("/api/agente/relatorio")
async def api_agente_relatorio():
    """Último relatório do agente."""
    rel = obter_ultimo_relatorio()
    return JSONResponse(json.loads(json.dumps(rel or {}, default=str)))


# ============================================================
# OUTREACH REGRAS — API CRUD
# ============================================================

@app.get("/api/outreach/regras")
async def api_outreach_regras():
    """Lista todas as regras de outreach."""
    regras = listar_outreach_regras_todas()
    return JSONResponse(json.loads(json.dumps(regras, default=str)))


@app.post("/api/outreach/regras")
async def api_criar_outreach_regra(request: Request):
    """Cria nova regra de outreach."""
    body = await request.json()
    nome = body.get("nome", "").strip()
    condicao = body.get("condicao", {})
    acoes = body.get("acoes")
    prioridade = int(body.get("prioridade", 0))
    if not nome:
        return JSONResponse({"erro": "Nome obrigatório"}, status_code=400)
    regra_id = criar_outreach_regra(nome, condicao, acoes, prioridade)
    return JSONResponse({"ok": True, "id": regra_id})


@app.put("/api/outreach/regras/{regra_id}")
async def api_atualizar_outreach_regra(regra_id: int, request: Request):
    """Atualiza regra de outreach."""
    body = await request.json()
    ok = atualizar_outreach_regra(regra_id, **body)
    if not ok:
        return JSONResponse({"erro": "Regra não encontrada"}, status_code=404)
    return JSONResponse({"ok": True})


@app.delete("/api/outreach/regras/{regra_id}")
async def api_deletar_outreach_regra(regra_id: int):
    """Deleta regra de outreach."""
    ok = deletar_outreach_regra(regra_id)
    if not ok:
        return JSONResponse({"erro": "Regra não encontrada"}, status_code=404)
    return JSONResponse({"ok": True})


@app.post("/api/configuracao")
async def api_configuracao_set(request: Request):
    """Salva uma configuração individual (toggle on/off ou valor)."""
    body = await request.json()
    chave = body.get("chave", "").strip()
    valor = str(body.get("valor", "")).strip()
    if not chave:
        return JSONResponse({"erro": "Chave obrigatória"}, status_code=400)

    # Validar chaves permitidas (toggles + configs)
    chaves_permitidas = {
        "audio_stt_ativo", "audio_tts_autonomo", "audio_voz",
        "retry_ativo", "retry_max",
        "cooling_ativo", "cooling_dias", "cooling_max_sem_resposta",
        "regras_auto_ativo",
        "outreach_ativo", "outreach_max_email_dia",
        "wa_sales_ativo",
    }
    if chave not in chaves_permitidas:
        return JSONResponse({"erro": f"Chave não permitida: {chave}"}, status_code=400)

    salvar_configuracao(chave, valor)
    return JSONResponse({"ok": True, "chave": chave, "valor": valor})


@app.get("/api/configuracao/toggles")
async def api_configuracao_toggles():
    """Retorna todos os toggles de controle do sistema."""
    configs = obter_configuracoes_todas()
    toggles = {
        "audio_stt_ativo": configs.get("audio_stt_ativo", "true") == "true",
        "audio_tts_autonomo": configs.get("audio_tts_autonomo", "true") == "true",
        "audio_voz": "fish_s2pro",  # Fish Audio S2-Pro (ÚNICO provider)
        "retry_ativo": configs.get("retry_ativo", "true") == "true",
        "retry_max": int(configs.get("retry_max", "3")),
        "cooling_ativo": configs.get("cooling_ativo", "true") == "true",
        "cooling_dias": int(configs.get("cooling_dias", "7")),
        "cooling_max_sem_resposta": int(configs.get("cooling_max_sem_resposta", "3")),
        "regras_auto_ativo": configs.get("regras_auto_ativo", "true") == "true",
        "outreach_ativo": configs.get("outreach_ativo", "false") == "true",
        "outreach_max_email_dia": int(configs.get("outreach_max_email_dia", "20")),
    }
    return JSONResponse(toggles)


@app.post("/api/outreach/ativar")
async def api_outreach_ativar():
    """Ativa outreach automático."""
    salvar_configuracao("outreach_ativo", "true")
    return JSONResponse({"ok": True, "outreach_ativo": True})


@app.post("/api/outreach/desativar")
async def api_outreach_desativar():
    """Desativa outreach automático."""
    salvar_configuracao("outreach_ativo", "false")
    return JSONResponse({"ok": True, "outreach_ativo": False})


# ============================================================
# SALES AUTOPILOT — INTERFACE PRINCIPAL
# ============================================================

@app.get("/autopilot", response_class=HTMLResponse)
async def autopilot_page(request: Request):
    """Sales Autopilot — interface principal com 4 abas."""
    metricas = autopilot_metricas()
    funil = autopilot_funil()
    config = autopilot_config()
    decisoes = autopilot_decisoes_recentes(10)
    leads_quentes = autopilot_leads_quentes(10)
    conversas = autopilot_conversas_formatadas(30)
    experimentos_data = listar_experimentos(ativo=False)

    # Formatar experimentos para o template
    exps_fmt = []
    for e in experimentos_data[:10]:
        exps_fmt.append({
            "variavel": e.get("variavel", ""),
            "vencedor": e.get("vencedor") or (e.get("variante_a", "") + " vs " + e.get("variante_b", "")),
            "confianca": e.get("confianca_pct") or 0,
            "status": "aplicado" if e.get("vencedor") else "rodando",
        })

    # Regras de outreach
    regras = listar_outreach_regras_todas()
    configs_all = obter_configuracoes_todas()
    outreach_ativo = configs_all.get("outreach_ativo", "false") == "true"

    return templates.TemplateResponse("autopilot.html", {
        "request": request,
        "metricas": metricas,
        "funil": funil,
        "config": config,
        "decisoes": decisoes,
        "leads_quentes": leads_quentes,
        "conversas": conversas,
        "experimentos": exps_fmt,
        "regras": regras,
        "outreach_ativo": outreach_ativo,
    })


@app.get("/api/autopilot/conversas")
async def api_autopilot_conversas():
    """Lista conversas formatadas para o autopilot."""
    convs = autopilot_conversas_formatadas(30)
    return JSONResponse(json.loads(json.dumps(convs, default=str)))


@app.get("/api/autopilot/conversa/{conversa_id}")
async def api_autopilot_conversa(conversa_id: int):
    """Detalhe de conversa para o autopilot."""
    conv = autopilot_conversa_detalhe(conversa_id)
    if not conv:
        return JSONResponse({"erro": "Conversa não encontrada"}, status_code=404)
    return JSONResponse(json.loads(json.dumps(conv, default=str)))


@app.post("/api/autopilot/conversa/{conversa_id}/assumir")
async def api_autopilot_assumir(conversa_id: int):
    """Humano assume controle da conversa."""
    from datetime import datetime
    ok = atualizar_conversa_wa(conversa_id, handoff_at=datetime.now(),
                                handoff_motivo="Controle manual")
    return JSONResponse({"ok": ok})


@app.post("/api/autopilot/conversa/{conversa_id}/devolver")
async def api_autopilot_devolver(conversa_id: int):
    """Devolver conversa ao robô."""
    ok = atualizar_conversa_wa(conversa_id, status="ativo")
    # Limpar handoff (precisa query direta)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_conversas SET handoff_at = NULL, handoff_motivo = NULL
            WHERE id = %s
        """, (conversa_id,))
        conn.commit()
    return JSONResponse({"ok": True})


@app.post("/api/autopilot/conversa/{conversa_id}/pausar")
async def api_autopilot_pausar(conversa_id: int):
    """Pausar conversa."""
    ok = atualizar_conversa_wa(conversa_id, status="pausado")
    return JSONResponse({"ok": ok})


@app.post("/api/autopilot/conversa/{conversa_id}/enviar")
async def api_autopilot_enviar_manual(request: Request, conversa_id: int):
    """Enviar mensagem manual na conversa."""
    body = await request.json()
    texto = body.get("mensagem", "").strip()
    if not texto:
        return JSONResponse({"erro": "Mensagem vazia"}, status_code=400)

    from crm.database import registrar_msg_wa
    msg_id = registrar_msg_wa(conversa_id, "enviada", texto, tipo="texto")

    # Enviar via WhatsApp
    conv = obter_conversa_wa(conversa_id)
    if conv and conv.get("numero_envio"):
        try:
            from crm.wa_sales_bot import enviar_mensagem_wa
            enviar_mensagem_wa(conv["numero_envio"], texto)
        except Exception as e:
            print(f"[AUTOPILOT] Erro ao enviar WA: {e}")

    return JSONResponse({"ok": True, "msg_id": msg_id})


# ============================================================
# MONITORAMENTO TOKENS xAI/GROK
# ============================================================

@app.get("/api/tokens/usage")
async def api_tokens_usage():
    """Retorna uso de tokens do xAI com estimativas de custo e conversas restantes."""
    import httpx as _httpx

    xai_key = os.environ.get("XAI_API_KEY", "")
    if not xai_key:
        return JSONResponse({"erro": "XAI_API_KEY não configurada"}, status_code=500)

    # Pricing por modelo (por milhão de tokens)
    PRICING = {
        "grok-3-mini": {"input": 0.10, "output": 0.30},
        "grok-3-fast": {"input": 5.00, "output": 25.00},
        "grok-3": {"input": 2.00, "output": 10.00},
        "grok-4-1-fast": {"input": 0.20, "output": 0.50},
    }

    # Buscar uso de tokens dos últimos 30 dias via contagem local de mensagens WA
    with get_conn() as conn:
        cur = conn.cursor()

        # Msgs geradas por Grok (flag grok=True) — estimativa de tokens
        cur.execute("""
            SELECT COUNT(*) as total_msgs,
                   COALESCE(SUM(LENGTH(conteudo)), 0) as total_chars,
                   COUNT(CASE WHEN created_at::date = CURRENT_DATE THEN 1 END) as msgs_hoje,
                   COALESCE(SUM(CASE WHEN created_at::date = CURRENT_DATE THEN LENGTH(conteudo) ELSE 0 END), 0) as chars_hoje,
                   COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as msgs_7d,
                   COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN LENGTH(conteudo) ELSE 0 END), 0) as chars_7d
            FROM wa_mensagens
            WHERE grok_resposta = TRUE
        """)
        grok_stats = dict(cur.fetchone() or {})

        # Total de conversas ativas
        cur.execute("SELECT COUNT(*) as total FROM wa_conversas WHERE status = 'ativo'")
        conversas_ativas = (cur.fetchone() or {}).get("total", 0)

        # Total de conversas nos últimos 7 dias
        cur.execute("""
            SELECT COUNT(DISTINCT lead_id) as total
            FROM wa_conversas
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        conversas_7d = (cur.fetchone() or {}).get("total", 0)

    # Estimativa de tokens (1 char ≈ 0.3 tokens para português)
    # Input: system prompt (~4000 tokens) + histórico (~2000 por turno) + knowledge base (~3000)
    # Output: ~200 tokens por resposta
    total_msgs = grok_stats.get("total_msgs", 0)
    total_chars_output = grok_stats.get("total_chars", 0)
    msgs_hoje = grok_stats.get("msgs_hoje", 0)
    msgs_7d = grok_stats.get("msgs_7d", 0)

    est_tokens_output = int(total_chars_output * 0.3)
    est_tokens_input = total_msgs * 7000  # ~7K tokens input por resposta (prompt + hist + kb)
    est_tokens_output_hoje = int(grok_stats.get("chars_hoje", 0) * 0.3)
    est_tokens_input_hoje = msgs_hoje * 7000

    # Modelo atual
    modelo_atual = "grok-3-mini"
    pricing = PRICING.get(modelo_atual, PRICING["grok-3-mini"])

    # Custo estimado
    custo_input = (est_tokens_input / 1_000_000) * pricing["input"]
    custo_output = (est_tokens_output / 1_000_000) * pricing["output"]
    custo_total = custo_input + custo_output

    custo_input_hoje = (est_tokens_input_hoje / 1_000_000) * pricing["input"]
    custo_output_hoje = (est_tokens_output_hoje / 1_000_000) * pricing["output"]
    custo_hoje = custo_input_hoje + custo_output_hoje

    # Custo médio por conversa (10 turnos de média)
    custo_por_conversa = 10 * ((7000 / 1_000_000 * pricing["input"]) + (200 / 1_000_000 * pricing["output"]))

    # Saldo — tentar buscar na xAI Management API
    saldo = None
    saldo_erro = None
    uso_real = None
    mgmt_key = os.environ.get("XAI_MANAGEMENT_KEY", "")
    xai_team_id = os.environ.get("XAI_TEAM_ID", "2af4fd37-244c-4101-9f32-1de3c2554208")
    if mgmt_key:
        mgmt_headers = {"Authorization": f"Bearer {mgmt_key}", "Content-Type": "application/json"}
        # 1. Saldo (crédito pré-pago)
        try:
            resp = _httpx.get(
                f"https://management-api.x.ai/v1/billing/teams/{xai_team_id}/prepaid/balance",
                headers=mgmt_headers, timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                total_val = data.get("total", {}).get("val", "0")
                saldo = abs(int(total_val)) / 100
        except Exception as e:
            saldo_erro = str(e)

        # 2. Uso real via Management API (este mês)
        try:
            from datetime import date as _date
            primeiro_dia = _date.today().replace(day=1).strftime("%Y-%m-%d 00:00:00")
            hoje = _date.today().strftime("%Y-%m-%d 23:59:59")
            resp_uso = _httpx.post(
                f"https://management-api.x.ai/v1/billing/teams/{xai_team_id}/usage",
                headers=mgmt_headers, timeout=10,
                json={"analyticsRequest": {
                    "timeRange": {"startTime": primeiro_dia, "endTime": hoje, "timezone": "America/Sao_Paulo"},
                    "timeUnit": "TIME_UNIT_NONE",
                    "values": [{"name": "usd", "aggregation": "AGGREGATION_SUM"}],
                    "groupBy": ["description"], "filters": [],
                }},
            )
            if resp_uso.status_code == 200:
                data_uso = resp_uso.json()
                uso_total = 0.0
                modelos_uso = {}
                for ts in data_uso.get("timeSeries", []):
                    modelo = (ts.get("groupLabels") or ["?"])[0]
                    valor = sum(dp.get("values", [0])[0] for dp in ts.get("dataPoints", []))
                    uso_total += valor
                    modelos_uso[modelo] = round(valor, 6)
                uso_real = {"total_usd": round(uso_total, 4), "por_modelo": modelos_uso}
        except Exception:
            pass

    # Saldo disponível = crédito comprado - uso real
    saldo_disponivel = None
    if saldo is not None and uso_real:
        saldo_disponivel = round(saldo - uso_real["total_usd"], 4)

    # Previsão de conversas restantes (usando saldo real da Management API)
    conversas_restantes = None
    saldo_para_previsao = saldo_disponivel if saldo_disponivel is not None else (saldo - custo_total if saldo else None)
    if saldo_para_previsao is not None and custo_por_conversa > 0:
        conversas_restantes = max(0, int(saldo_para_previsao / custo_por_conversa))

    return JSONResponse({
        "modelo_atual": modelo_atual,
        "pricing": pricing,
        "saldo_usd": saldo,
        "saldo_disponivel_usd": saldo_disponivel,
        "uso_real_usd": uso_real,
        "saldo_erro": saldo_erro,
        "saldo_brl_estimado": round((saldo_disponivel or saldo or 0) * 5.5, 2),
        "console_url": f"https://console.x.ai/team/{xai_team_id}/billing",
        "uso": {
            "total_respostas_grok": total_msgs,
            "respostas_hoje": msgs_hoje,
            "respostas_7d": msgs_7d,
            "conversas_ativas": conversas_ativas,
            "conversas_7d": conversas_7d,
        },
        "tokens_estimados": {
            "input_total": est_tokens_input,
            "output_total": est_tokens_output,
            "input_hoje": est_tokens_input_hoje,
            "output_hoje": est_tokens_output_hoje,
        },
        "custo_estimado_usd": {
            "total": round(custo_total, 4),
            "hoje": round(custo_hoje, 4),
            "por_conversa_media": round(custo_por_conversa, 4),
        },
        "previsao": {
            "conversas_restantes": conversas_restantes,
            "dias_restantes": round(conversas_restantes / max(1, conversas_7d / 7), 1) if conversas_restantes else None,
        },
        "dica": "Para ver saldo real: configure XAI_MANAGEMENT_KEY nas secrets ou acesse " + "https://console.x.ai/team/default/billing",
    })


# ============================================================
# ADMIN BRAIN — CHAT NL (Fase 5)
# ============================================================

@app.get("/brain", response_class=HTMLResponse)
async def brain_page(request: Request):
    """Interface de chat Brain (linguagem natural)."""
    return templates.TemplateResponse("brain.html", {
        "request": request,
        "pagina_ativa": "brain",
    })


@app.post("/api/admin/brain/chat")
async def api_brain_chat(request: Request):
    """Endpoint de chat Brain — envia mensagem, recebe resposta com function calling."""
    from crm.admin_brain import chat
    body = await request.json()
    mensagem = body.get("mensagem", "").strip()
    historico = body.get("historico", [])

    if not mensagem:
        return JSONResponse({"erro": "Mensagem vazia"}, status_code=400)

    try:
        resultado = chat(mensagem, historico)
        return JSONResponse(resultado)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"erro": str(e)}, status_code=500)


# ============================================================
# AUDIO CACHE + TTS STATUS — Endpoints Admin
# ============================================================

@app.get("/api/audio-cache")
async def api_listar_audio_cache(limite: int = 50, offset: int = 0):
    """Lista cache de áudios TTS (paginado, ordenado por vezes_usado DESC)."""
    from crm.audio_cache import listar_cache
    return JSONResponse(listar_cache(limite, offset))


@app.get("/api/audio-cache/stats")
async def api_stats_audio_cache():
    """Estatísticas do cache: total, hits, economia estimada."""
    from crm.audio_cache import stats_cache
    from crm.tts_queue import tts_queue
    cache_stats = stats_cache()
    queue_status = tts_queue.status
    cache_stats["tts_queue"] = queue_status.get("metrics", {})
    return JSONResponse(cache_stats)


@app.delete("/api/audio-cache")
async def api_limpar_audio_cache():
    """Limpa todo o cache de áudios."""
    from crm.audio_cache import invalidar_cache
    count = invalidar_cache()
    return JSONResponse({"invalidados": count})


@app.delete("/api/audio-cache/{intent_key}")
async def api_limpar_audio_cache_intent(intent_key: str):
    """Limpa cache de áudios por intent_key específica."""
    from crm.audio_cache import invalidar_cache
    count = invalidar_cache(intent_key)
    return JSONResponse({"intent_key": intent_key, "invalidados": count})


@app.get("/api/tts/status")
async def api_tts_status():
    """Status da fila TTS: slots ativos, métricas, provider."""
    from crm.tts_queue import tts_queue
    return JSONResponse(tts_queue.status)


# ============================================================
# SYNC API — Scraper remoto → CRM via HTTPS
# ============================================================

def _verify_sync_api_key(request: Request) -> bool:
    """Valida API key do scraper remoto."""
    if not CRM_SYNC_API_KEY:
        return False
    api_key = request.headers.get("X-API-Key", "")
    return secrets.compare_digest(api_key, CRM_SYNC_API_KEY)


@app.get("/api/health/sync")
async def api_health_sync():
    """Health check público para o scraper verificar conectividade."""
    from datetime import datetime as dt
    has_key = bool(CRM_SYNC_API_KEY)
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as c FROM leads")
            total = cur.fetchone()["c"]
        db_ok = True
    except Exception:
        total = 0
        db_ok = False
    return JSONResponse({
        "status": "ok" if db_ok else "degraded",
        "api_key_configured": has_key,
        "total_leads": total,
        "timestamp": dt.now().isoformat(),
    })


@app.post("/api/leads/sync")
async def api_leads_sync(request: Request):
    """Recebe batch de leads do scraper remoto e faz upsert no PostgreSQL.

    Headers: X-API-Key: <CRM_SYNC_API_KEY>
    Body JSON: {"leads": [...], "source": "scraper", "cidade": "MACEIO", "uf": "AL"}
    Max: 100 leads por batch.
    """
    if not _verify_sync_api_key(request):
        return JSONResponse({"erro": "API key inválida"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"erro": "JSON inválido"}, status_code=400)

    leads = body.get("leads", [])
    source = body.get("source", "sync_api")
    cidade = body.get("cidade", "")
    uf = body.get("uf", "")

    if not leads:
        return JSONResponse({"erro": "Lista de leads vazia"}, status_code=400)

    if len(leads) > 100:
        return JSONResponse({"erro": f"Máximo 100 leads por batch (recebido: {len(leads)})"}, status_code=400)

    try:
        stats = upsert_leads_batch(leads, source=source)
        return JSONResponse({
            "ok": True,
            "inseridos": stats["inseridos"],
            "atualizados": stats["atualizados"],
            "erros": stats["erros"],
            "cidade": cidade,
            "uf": uf,
            "detalhes_erros": stats["detalhes_erros"][:10],
        })
    except Exception as e:
        return JSONResponse({"erro": f"Erro no upsert: {str(e)[:200]}"}, status_code=500)


# ============================================================
# P2.3: HANDOFF FILA — Dashboard de Conversas Handoff
# ============================================================

@app.get("/api/handoff/fila")
async def api_handoff_fila():
    """Lista conversas em handoff com dados do lead, score, tempo em espera."""
    conversas = conversas_handoff_sem_resposta(0)  # Todas em handoff
    fila = []
    for c in conversas:
        lead = obter_lead(c.get("lead_id")) if c.get("lead_id") else {}
        fila.append({
            "conversa_id": c["id"],
            "lead_id": c.get("lead_id"),
            "nome": (lead.get("nome_fantasia") or lead.get("razao_social") or "Desconhecido") if lead else "Desconhecido",
            "cidade": lead.get("cidade", "") if lead else "",
            "score": lead.get("lead_score", 0) if lead else 0,
            "tier": lead.get("tier", "") if lead else "",
            "numero": c.get("numero_envio", ""),
            "motivo": c.get("handoff_motivo", ""),
            "handoff_at": str(c.get("handoff_at") or ""),
            "ultima_msg": str(c.get("updated_at") or ""),
            "msgs_recebidas": c.get("msgs_recebidas", 0),
            "persona": c.get("persona_detectada", ""),
            "followup_etapa": c.get("followup_handoff_etapa", 0),
        })
    return JSONResponse(json.loads(json.dumps(fila, default=str)))


@app.post("/api/handoff/{conversa_id}/responder")
async def api_handoff_responder(conversa_id: int, request: Request):
    """Humano responde ao lead pelo CRM (envia WA via Evolution/Meta)."""
    body = await request.json()
    texto = body.get("mensagem", "").strip()
    if not texto:
        return JSONResponse({"erro": "Mensagem vazia"}, status_code=400)

    from crm.database import registrar_msg_wa
    msg_id = registrar_msg_wa(conversa_id, "enviada", texto, tipo="texto")

    conv = obter_conversa_wa(conversa_id)
    if conv and conv.get("numero_envio"):
        try:
            from crm.wa_sales_bot import _enviar_direto
            _enviar_direto(conv["numero_envio"], texto)
        except Exception as e:
            return JSONResponse({"erro": f"Falha ao enviar: {e}"}, status_code=500)

    return JSONResponse({"ok": True, "msg_id": msg_id})


@app.post("/api/handoff/{conversa_id}/devolver")
async def api_handoff_devolver_bot(conversa_id: int):
    """Devolve conversa ao bot (sai do handoff)."""
    ok = atualizar_conversa_wa(conversa_id, status="ativo")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_conversas SET handoff_at = NULL, handoff_motivo = NULL
            WHERE id = %s
        """, (conversa_id,))
        conn.commit()
    return JSONResponse({"ok": True})


@app.get("/handoff", response_class=HTMLResponse)
async def handoff_fila_page(request: Request):
    """Página da fila de handoff."""
    return templates.TemplateResponse("handoff_fila.html", {
        "request": request,
        "pagina_ativa": "handoff",
    })


# ============================================================
# P4.3: CONVERSÃO — Endpoint chamado pelo backend principal
# ============================================================

@app.post("/api/leads/{cnpj}/conversao")
async def api_registrar_conversao(cnpj: str, request: Request):
    """Registra conversão de lead. Chamado pelo backend principal quando restaurante ativa conta.
    Protegido por API key (CRM_SYNC_API_KEY)."""
    if not _verify_sync_api_key(request):
        return JSONResponse({"erro": "API key inválida"}, status_code=401)

    body = await request.json()
    plano = body.get("plano", "basico")
    valor_mensal = float(body.get("valor_mensal", 169.90))

    lead = buscar_lead_por_cnpj(cnpj)
    if not lead:
        return JSONResponse({"erro": f"Lead com CNPJ {cnpj} não encontrado"}, status_code=404)

    lead_id = lead["id"]

    # Determinar canal de atribuição
    from crm.metricas_roi import determinar_canal_atribuicao
    canal = determinar_canal_atribuicao(lead_id)

    # Registrar conversão
    conversao_id = registrar_conversao(lead_id, plano, valor_mensal, canal, cnpj)

    # P4.3: Feedback de conversão (scoring)
    try:
        from crm.scoring import feedback_conversao
        feedback_conversao(cnpj)
    except Exception as e:
        print(f"[CONVERSAO] Erro no feedback scoring: {e}")

    return JSONResponse({
        "ok": True,
        "conversao_id": conversao_id,
        "lead_id": lead_id,
        "canal_atribuicao": canal,
        "plano": plano,
        "valor_mensal": valor_mensal,
    })


# ============================================================
# P5.4: MÉTRICAS ROI — Dashboard
# ============================================================

@app.get("/api/metricas/roi")
async def api_metricas_roi():
    """KPIs financeiros: CAC, LTV, ROI, canais, receita."""
    from crm.metricas_roi import metricas_roi_completas
    try:
        metricas = metricas_roi_completas()
        return JSONResponse(json.loads(json.dumps(metricas, default=str)))
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)


@app.get("/api/metricas/funil-conversao")
async def api_funil_conversao():
    """Funil de conversão: leads → contactados → responderam → demo → trial → cliente."""
    from crm.metricas_roi import metricas_funil_conversao
    try:
        funil = metricas_funil_conversao()
        return JSONResponse(json.loads(json.dumps(funil, default=str)))
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)


@app.get("/api/metricas/atribuicao/{lead_id}")
async def api_atribuicao_lead(lead_id: int):
    """Multi-touch attribution para um lead específico."""
    from crm.metricas_roi import atribuicao_lead
    try:
        touchpoints = atribuicao_lead(lead_id)
        return JSONResponse(json.loads(json.dumps(touchpoints, default=str)))
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)
