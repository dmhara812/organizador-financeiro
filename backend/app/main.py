from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Usar uma função fábrica facilita testes futuros, porque poderemos criar instâncias
    isoladas da aplicação com configurações específicas para ambiente de teste.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API para controle de patrimônio, aportes e evolução de investimentos.",
        debug=settings.debug,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
