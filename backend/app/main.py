from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings


def create_application() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Usar uma função de criação facilita testes e mantém a configuração da app em
    um ponto único. Nas próximas etapas, middlewares, handlers globais de erro e
    routers de domínio serão adicionados aqui de forma controlada.
    """

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Todas as rotas versionadas entram sob `/api/v1`, mantendo espaço para
    # versões futuras sem quebrar contratos já usados pelo frontend.
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_application()
