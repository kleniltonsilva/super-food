"""
crm/scanner.py - Orquestrador de scans do CRM
Executa pipeline de scraping direto do CRM usando PostgreSQL.
"""
import asyncio
import sys
import os
import traceback
import logging
from datetime import datetime

logger = logging.getLogger("scanner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[SCANNER] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Garantir que o diretório raiz esteja no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db_pg import (
        init_pg, criar_scan_job, atualizar_scan_job, scan_log,
        obter_cnpjs_sem_ifood, obter_cnpjs_sem_delivery,
        atualizar_ifood_receita, atualizar_delivery_receita,
        buscar_cnpjs_para_maps_direcionado, atualizar_lead_maps,
        marcar_maps_checked, obter_scan_job,
    )
    logger.info("db_pg importado com sucesso")
except ImportError as e:
    logger.error(f"FALHA ao importar db_pg: {e}")
    raise

try:
    from config import DELIVERY_PLATAFORMAS, normalizar_cidade
    logger.info("config importado com sucesso")
except ImportError as e:
    logger.error(f"FALHA ao importar config: {e}")
    raise


# Scan ativo (para controlar cancelamento)
_scan_tasks = {}


def _check_cancelled(job_id: int) -> bool:
    """Verifica no BD se o job foi marcado como 'cancelando' ou 'cancelado'."""
    try:
        job = obter_scan_job(job_id)
        if job and job.get("status") in ("cancelando", "cancelado"):
            return True
    except Exception as e:
        logger.warning(f"[job={job_id}] _check_cancelled falhou: {e}")
    return False


def _safe_scan_log(job_id: int, message: str, level: str = "info"):
    """scan_log que não lança exceção — fallback para logger se BD falhar."""
    try:
        scan_log(job_id, message, level)
    except Exception as e:
        logger.error(f"[job={job_id}] scan_log falhou ({e}): {message}")


def _safe_update_job(job_id: int, **kwargs):
    """atualizar_scan_job que não lança exceção."""
    try:
        atualizar_scan_job(job_id, **kwargs)
    except Exception as e:
        logger.error(f"[job={job_id}] atualizar_scan_job falhou ({e}): {kwargs}")


async def executar_scan(job_id: int, cidades: list, etapas: list,
                         headless: bool = True):
    """Executa pipeline de scan completo.

    Args:
        job_id: ID do scan_job no banco
        cidades: Lista de [cidade, uf]
        etapas: Lista de etapas: 'maps', 'ifood', 'rappi', '99food'
        headless: Modo headless do browser
    """
    logger.info(f"[job={job_id}] executar_scan iniciado: {len(cidades)} cidades, etapas={etapas}")

    try:
        init_pg()
    except Exception as e:
        logger.error(f"[job={job_id}] FALHA init_pg: {e}\n{traceback.format_exc()}")
        return

    _safe_update_job(job_id, status="executando", started_at=datetime.now())
    _safe_scan_log(job_id, f"Scan iniciado: {len(cidades)} cidade(s), etapas: {', '.join(etapas)}")

    total_processados = 0
    total_encontrados = 0
    total_erros = 0
    progresso = {}

    try:
        for i, (cidade, uf) in enumerate(cidades):
            # Verificar cancelamento antes de cada cidade
            if _check_cancelled(job_id):
                _safe_scan_log(job_id, "Cancelamento detectado antes de iniciar cidade.", "warning")
                raise asyncio.CancelledError()

            cidade_norm = normalizar_cidade(cidade)
            cidade_key = f"{cidade_norm}/{uf}"
            progresso[cidade_key] = {"status": "executando", "etapas": {}}

            _safe_update_job(job_id,
                             cidade_atual=f"{cidade_norm}/{uf}",
                             progresso=progresso)
            _safe_scan_log(job_id, f"{'='*50}")
            _safe_scan_log(job_id, f"Cidade {i+1}/{len(cidades)}: {cidade_norm}/{uf}")
            _safe_scan_log(job_id, f"{'='*50}")

            # Maps Direcionada
            if "maps" in etapas:
                try:
                    stats = await _etapa_maps_direcionado(
                        job_id, cidade_norm, uf, headless
                    )
                    progresso[cidade_key]["etapas"]["maps"] = stats
                    total_processados += stats.get("processados", 0)
                    total_encontrados += stats.get("encontrados", 0)
                except Exception as e:
                    total_erros += 1
                    tb = traceback.format_exc()
                    logger.error(f"[job={job_id}] Maps falhou: {e}\n{tb}")
                    _safe_scan_log(job_id, f"[ERRO] Maps: {e}\n{tb}", "error")
                    progresso[cidade_key]["etapas"]["maps"] = {"erro": str(e)}

            # Delivery platforms
            for plat in ["ifood", "rappi", "99food"]:
                if plat not in etapas:
                    continue
                # Verificar cancelamento antes de cada etapa
                if _check_cancelled(job_id):
                    _safe_scan_log(job_id, f"Cancelamento detectado antes de {plat}.", "warning")
                    raise asyncio.CancelledError()
                try:
                    stats = await _etapa_delivery(
                        job_id, cidade_norm, uf, plat, headless
                    )
                    progresso[cidade_key]["etapas"][plat] = stats
                    total_processados += stats.get("processados", 0)
                    total_encontrados += stats.get("encontrados", 0)
                except Exception as e:
                    total_erros += 1
                    tb = traceback.format_exc()
                    logger.error(f"[job={job_id}] {plat} falhou: {e}\n{tb}")
                    _safe_scan_log(job_id, f"[ERRO] {plat}: {e}\n{tb}", "error")
                    progresso[cidade_key]["etapas"][plat] = {"erro": str(e)}

            progresso[cidade_key]["status"] = "concluido"
            _safe_update_job(job_id,
                             processados=total_processados,
                             encontrados=total_encontrados,
                             erros=total_erros,
                             progresso=progresso)

        _safe_update_job(job_id,
                         status="concluido",
                         finished_at=datetime.now(),
                         processados=total_processados,
                         encontrados=total_encontrados,
                         erros=total_erros,
                         progresso=progresso)
        _safe_scan_log(job_id, f"Scan concluido! Processados: {total_processados}, "
                               f"Encontrados: {total_encontrados}, Erros: {total_erros}")

    except asyncio.CancelledError:
        _safe_update_job(job_id, status="cancelado",
                         finished_at=datetime.now())
        _safe_scan_log(job_id, "Scan cancelado pelo usuario.", "warning")
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[job={job_id}] Scan falhou FATALMENTE: {e}\n{tb}")
        _safe_update_job(job_id, status="erro",
                         finished_at=datetime.now(),
                         erros=total_erros + 1)
        _safe_scan_log(job_id, f"Scan falhou: {e}\n{tb}", "error")
    finally:
        _scan_tasks.pop(job_id, None)


async def _etapa_maps_direcionado(job_id: int, cidade: str, uf: str,
                                    headless: bool) -> dict:
    """Executa busca Maps direcionada para uma cidade."""
    _safe_scan_log(job_id, f"[MAPS] Iniciando busca direcionada: {cidade}/{uf}")
    _safe_update_job(job_id, etapa_atual="maps")

    cnpjs = buscar_cnpjs_para_maps_direcionado(cidade, uf)
    if not cnpjs:
        _safe_scan_log(job_id, f"[MAPS] Nenhum CNPJ pendente em {cidade}/{uf}")
        return {"processados": 0, "encontrados": 0, "msg": "nenhum pendente"}

    _safe_scan_log(job_id, f"[MAPS] {len(cnpjs)} CNPJs para buscar em {cidade}/{uf}")

    # Importar scraper com logging
    try:
        from gmaps_scraper import scrape_maps_direcionado
        logger.info(f"[job={job_id}] gmaps_scraper importado com sucesso")
    except ImportError as e:
        msg = f"[MAPS] FALHA ao importar gmaps_scraper: {e}"
        logger.error(msg)
        _safe_scan_log(job_id, msg, "error")
        return {"processados": 0, "encontrados": 0, "erro": str(e)}

    encontrados = 0

    def on_match(dados_maps, dados_cnpj):
        nonlocal encontrados
        cnpj = dados_cnpj.get("cnpj", "")
        score = dados_maps.get("score_match", 0)
        atualizar_lead_maps(cnpj, dados_maps, score)
        encontrados += 1
        _safe_scan_log(job_id, f"[MAPS] Match: {cnpj} -> {dados_maps.get('nome', '')[:40]} (score={score:.2f})")

    stats = await scrape_maps_direcionado(cidade, uf, headless, callback=on_match)

    # Marcar CNPJs nao encontrados como checked
    total = stats.get("total", 0)
    _safe_scan_log(job_id, f"[MAPS] {cidade}/{uf}: {encontrados}/{total} encontrados")

    return {"processados": total, "encontrados": encontrados}


async def _etapa_delivery(job_id: int, cidade: str, uf: str,
                           plataforma: str, headless: bool) -> dict:
    """Executa verificacao delivery para uma cidade/plataforma."""
    config = DELIVERY_PLATAFORMAS.get(plataforma, {})
    nome_plat = config.get("nome", plataforma)

    _safe_scan_log(job_id, f"[{nome_plat}] Iniciando verificacao: {cidade}/{uf}")
    _safe_update_job(job_id, etapa_atual=plataforma)

    # Buscar leads pendentes
    if plataforma == "ifood":
        pendentes = obter_cnpjs_sem_ifood(cidade, uf)
    else:
        pendentes = obter_cnpjs_sem_delivery(cidade, uf, plataforma)

    if not pendentes:
        _safe_scan_log(job_id, f"[{nome_plat}] Todos leads de {cidade}/{uf} ja verificados")
        return {"processados": 0, "encontrados": 0, "msg": "todos verificados"}

    # Preparar items
    items = []
    for r in pendentes:
        nome = r.get("nome_maps") or r.get("nome_fantasia") or ""
        if not nome or nome == r.get("razao_social", ""):
            nome_maps = r.get("nome_maps") or ""
            if nome_maps:
                nome = nome_maps
            else:
                continue
        items.append({"id": r["cnpj"], "nome": nome, "cidade": cidade})

    if not items:
        _safe_scan_log(job_id, f"[{nome_plat}] Nenhum lead com nome valido em {cidade}/{uf}")
        return {"processados": 0, "encontrados": 0, "msg": "sem nomes validos"}

    _safe_scan_log(job_id, f"[{nome_plat}] {len(items)} leads para verificar")

    # Importar delivery checker com logging
    try:
        from delivery_checker import verificar_plataforma_batch
        logger.info(f"[job={job_id}] delivery_checker importado com sucesso")
    except ImportError as e:
        msg = f"[{nome_plat}] FALHA ao importar delivery_checker: {e}"
        logger.error(msg)
        _safe_scan_log(job_id, msg, "error")
        return {"processados": 0, "encontrados": 0, "erro": str(e)}

    resultados = await verificar_plataforma_batch(items, plataforma, headless)

    # Resultados ja foram salvos individualmente pelo _processar_micro_batch
    com = sum(1 for r in resultados if r["tem"])
    _safe_scan_log(job_id, f"[{nome_plat}] {cidade}/{uf}: {com}/{len(resultados)} encontrados")

    return {"processados": len(resultados), "encontrados": com}


def iniciar_scan_background(job_id: int, cidades: list, etapas: list,
                              headless: bool = True):
    """Inicia scan como task asyncio em background.
    Chamado pelo FastAPI handler."""
    loop = asyncio.get_event_loop()
    task = loop.create_task(
        executar_scan(job_id, cidades, etapas, headless)
    )
    _scan_tasks[job_id] = task
    return task


def cancelar_scan(job_id: int) -> bool:
    """Cancela scan ativo."""
    task = _scan_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        return True
    return False
