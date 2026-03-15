# backend/app/logging_config.py

"""
Logging Configuration - Derekh Food API
Dev: console colorido | Prod: JSON stdout (Docker coleta)
"""

import logging
import sys
import os
import json
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """Formatter colorido para desenvolvimento"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Formatter JSON para producao (Docker/Cloud)"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        for field in ('request_id', 'tenant_id', 'method', 'path', 'status_code', 'duration_ms', 'client_ip'):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        if record.exc_info and record.exc_info[1]:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """Configura logging baseado no ambiente (ENVIRONMENT env var)"""
    environment = os.getenv("ENVIRONMENT", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColorFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S"
        ))

    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    logger = logging.getLogger("superfood")
    logger.info(f"Logging configurado: env={environment}, level={log_level}")

    return logger
