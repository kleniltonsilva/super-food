# bridge_agent/config.py

"""
Configuração do Bridge Agent.
Salva em %APPDATA%/DerekhBridge/bridge_config.json
"""

import json
import os
import logging

logger = logging.getLogger("bridge_agent.config")

DEFAULT_CONFIG = {
    "server_url": "https://superfood-api.fly.dev",
    "restaurante_id": None,
    "token": None,
    "impressoras_monitorar": [],
    "ignorar_prefixo": "Derekh_",
    "auto_criar_pedido": False,
    "codepage": "CP860",
    "poll_interval": 2.0,
    "auto_start": False,
}


def get_config_dir() -> str:
    """Retorna diretório de configuração (%APPDATA%/DerekhBridge/)."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = os.path.join(appdata, "DerekhBridge")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_path() -> str:
    return os.path.join(get_config_dir(), "bridge_config.json")


def get_log_dir() -> str:
    log_dir = os.path.join(get_config_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def load_config() -> dict:
    """Carrega configuração do disco ou retorna defaults."""
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config = {**DEFAULT_CONFIG, **saved}
            return config
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Erro ao ler config: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Salva configuração no disco."""
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Config salva em {path}")
    except IOError as e:
        logger.error(f"Erro ao salvar config: {e}")
