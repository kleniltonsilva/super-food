"""
Configuração do Sentry para monitoramento de erros.
Inicializa graciosamente — sem SENTRY_DSN, tudo funciona normalmente.
"""
import os
import logging

logger = logging.getLogger("superfood")


def init_sentry():
    """Inicializa Sentry SDK se SENTRY_DSN estiver configurado."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("Sentry: SENTRY_DSN não configurado — monitoramento desabilitado")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        environment = os.getenv("ENVIRONMENT", "development")

        def before_send(event, hint):
            """Filtra eventos que não queremos enviar ao Sentry."""
            # Ignora HTTPException do FastAPI (são respostas intencionais, não bugs)
            if "exc_info" in hint:
                exc = hint["exc_info"][1]
                from fastapi import HTTPException as FastAPIHTTPException
                if isinstance(exc, FastAPIHTTPException):
                    return None

            # Ignora 404
            if event.get("request", {}).get("url", ""):
                status = event.get("contexts", {}).get("response", {}).get("status_code")
                if status == 404:
                    return None

            # Ignora health checks
            request_url = event.get("request", {}).get("url", "")
            if any(p in request_url for p in ("/health", "/health/live", "/health/ready")):
                return None

            return event

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0,  # Sem performance tracing (free tier)
            before_send=before_send,
            release=f"derekh-food-api@{os.getenv('APP_VERSION', '4.0.0')}",
        )

        # Tag global
        sentry_sdk.set_tag("app_type", "api")

        logger.info(f"Sentry inicializado: environment={environment}")

    except ImportError:
        logger.warning("Sentry: sentry-sdk não instalado — pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.warning(f"Sentry: falha na inicialização — {e}")
