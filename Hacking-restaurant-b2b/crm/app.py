"""
app.py - Derekh CRM — FastAPI entry point + todas as rotas
"""
import sys
import os
import json
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crm.database import (
    init_pool, close_pool, init_schema,
    kpis_dashboard, funil_pipeline, distribuicao_segmento,
    top_cidades, followups_hoje, leads_quentes_sem_contato,
    stats_delivery, stats_delivery_por_cidade, cidades_escaneadas_ifood,
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

app = FastAPI(title="Derekh CRM")

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

templates.env.filters["format_number"] = format_number
templates.env.filters["format_currency"] = format_currency
templates.env.filters["format_date"] = format_date
templates.env.filters["format_datetime"] = format_datetime
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
    init_pg()  # Pool PG para scanner
    # Workers em background
    import asyncio
    asyncio.create_task(_outreach_loop())
    asyncio.create_task(_agente_loop())


async def _outreach_loop():
    """Worker que executa ações de outreach pendentes a cada 5 minutos."""
    import asyncio
    await asyncio.sleep(10)  # Esperar app inicializar
    while True:
        try:
            from crm.outreach_engine import executar_acoes_pendentes
            stats = executar_acoes_pendentes()
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
                resultado = ciclo_diario()
                print(f"[AGENTE-WORKER] Ciclo diário concluído: {resultado.get('relatorio_id')}")
                ultimo_dia = agora.date()
            except Exception as e:
                print(f"[AGENTE-WORKER] Erro: {e}")
        await asyncio.sleep(60)  # Verifica a cada 1 minuto

@app.on_event("shutdown")
async def shutdown():
    close_pool()


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
        "funil_json": json.dumps(funil, default=str),
        "segmentos_json": json.dumps(segmentos, default=str),
        "cidades_json": json.dumps(cidades, default=str),
        "delivery_json": json.dumps(delivery, default=str),
        "delivery_cidades_json": json.dumps(delivery_cidades, default=str),
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
    from crm.email_service import processar_webhook_resend
    payload = await request.json()
    resultado = processar_webhook_resend(payload)
    return JSONResponse(resultado)


# ============================================================
# SCORING (API)
# ============================================================

@app.get("/api/scoring/recalcular")
async def api_recalcular_scores(background_tasks: BackgroundTasks):
    from crm.scoring import calcular_scores_todos
    background_tasks.add_task(calcular_scores_todos)
    return RedirectResponse("/", status_code=303)


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

@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page(request: Request):
    """Pagina principal do scanner de leads."""
    init_pg()
    cidades = stats_cidades_scanner()
    jobs = listar_scan_jobs(20)
    scan_ativo = existe_scan_ativo()

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
    init_pg()

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

    # Iniciar em background
    from crm.scanner import iniciar_scan_background
    iniciar_scan_background(job_id, cidades_list, etapas_list, is_headless)

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
    """Cancela scan ativo."""
    from crm.scanner import cancelar_scan
    if cancelar_scan(job_id):
        return JSONResponse({"ok": True, "msg": "Scan cancelado"})
    atualizar_scan_job(job_id, status="cancelado")
    return JSONResponse({"ok": True, "msg": "Scan marcado como cancelado"})


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
    except Exception:
        pass  # Não falhar — pixel deve sempre retornar imagem
    return Response(content=PIXEL_GIF, media_type="image/gif",
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/tracking/click/{tracking_id}/{tipo}")
async def tracking_click(tracking_id: str, tipo: str, url: str = ""):
    """Registra clique e redireciona para URL destino."""
    try:
        marcar_email_clique(tracking_id, tipo)
    except Exception:
        pass
    destino = url or "https://derekh.com.br/food"
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
    stats = stats_outreach(dias)
    stats["emails_hoje"] = emails_enviados_hoje()
    stats["max_email_dia"] = int(obter_configuracoes_todas().get("outreach_max_email_dia", "20"))
    return JSONResponse(stats)


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

    return templates.TemplateResponse("outreach_dashboard.html", {
        "request": request,
        "stats": stats,
        "pendentes": pendentes,
        "futuras": futuras,
        "dist_tier": dist_tier,
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
async def wa_sales_audio(lead_id: int, voz: str = "ara"):
    """Envia áudio TTS personalizado para um lead."""
    from crm.wa_sales_bot import enviar_audio_wa
    result = enviar_audio_wa(lead_id, voz)
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


@app.post("/wa-sales/webhook")
async def wa_sales_webhook(request: Request):
    """Webhook WhatsApp Cloud API — mensagem recebida do lead."""
    from crm.wa_sales_bot import processar_resposta_wa, verificar_webhook_meta

    raw_body = await request.body()

    # Verificar assinatura HMAC-SHA256 (se configurado)
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature and not verificar_webhook_meta(raw_body, signature):
        return JSONResponse({"erro": "Assinatura inválida"}, status_code=403)

    body = json.loads(raw_body)

    # Meta Cloud API format:
    # {object: "whatsapp_business_account", entry: [{changes: [{value: {messages: [...]}}]}]}
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                numero = msg.get("from", "")
                msg_type = msg.get("type", "")
                if msg_type == "text":
                    texto = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    # Resposta de botão/lista
                    texto = (msg.get("interactive", {}).get("button_reply", {}).get("title", "")
                             or msg.get("interactive", {}).get("list_reply", {}).get("title", ""))
                else:
                    continue
                if numero and texto:
                    processar_resposta_wa(numero, texto)

    # Meta espera 200 rápido
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
