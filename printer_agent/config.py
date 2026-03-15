# printer_agent/config.py

"""
Gerenciamento de configuração do Printer Agent.
Armazena configurações em %APPDATA%/DerekhFood/printer_config.json
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("printer_agent.config")

DEFAULT_CONFIG = {
    "server_url": "wss://superfood-api.fly.dev",
    "restaurante_id": None,
    "token": None,
    "impressoras": {
        "geral": None,
        "cozinha": None,
        "bar": None,
        "caixa": None,
    },
    "largura_mm": 80,
    "codepage": "CP860",
    "auto_start": True,
    "copias": 1,
}


def get_app_dir() -> Path:
    """Retorna diretório de dados do app (%APPDATA%/DerekhFood)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", os.path.expanduser("~")))
    else:
        base = Path.home() / ".config"
    app_dir = base / "DerekhFood"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    return get_app_dir() / "printer_config.json"


def load_config() -> dict:
    """Carrega configuração do disco. Retorna defaults se não existir."""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge com defaults para campos novos
            config = {**DEFAULT_CONFIG, **saved}
            # Merge impressoras separadamente
            config["impressoras"] = {
                **DEFAULT_CONFIG["impressoras"],
                **saved.get("impressoras", {}),
            }
            return config
        except Exception as e:
            logger.warning(f"Erro ao carregar config: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Salva configuração no disco."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    logger.info(f"Config salva em {path}")


def is_configured(config: dict) -> bool:
    """Verifica se o agent está configurado (tem token e restaurante_id)."""
    return bool(config.get("token") and config.get("restaurante_id"))


def get_printer_for_setor(config: dict, setor: str) -> Optional[str]:
    """Retorna nome da impressora para o setor dado.
    Se o setor não tem impressora específica, usa 'geral'."""
    impressoras = config.get("impressoras", {})
    printer = impressoras.get(setor)
    if printer:
        return printer
    return impressoras.get("geral")


def has_multiple_printers(config: dict) -> bool:
    """Verifica se há múltiplas impressoras configuradas (split por setor)."""
    impressoras = config.get("impressoras", {})
    printers_set = set()
    for nome in impressoras.values():
        if nome:
            printers_set.add(nome)
    return len(printers_set) > 1
