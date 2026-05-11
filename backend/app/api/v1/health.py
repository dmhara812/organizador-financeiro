from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Verifica se a API está online")
def health_check() -> dict[str, str]:
    """Retorna o estado básico da aplicação.

    Este endpoint não consulta o banco, então ele ajuda a diferenciar problemas
    da aplicação HTTP de problemas específicos de infraestrutura do PostgreSQL.
    """

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/db", summary="Verifica se a API consegue acessar o banco")
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Executa uma consulta simples para validar a conexão com PostgreSQL.

    A resposta não expõe detalhes internos da exceção para evitar vazamento de
    informações sensíveis, como host, usuário ou string de conexão. Os detalhes
    completos devem ser observados nos logs do container durante desenvolvimento.
    """

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível no momento.",
        ) from exc

    return {"status": "ok", "database": "reachable"}
