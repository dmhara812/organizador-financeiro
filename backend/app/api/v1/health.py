from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import DatabaseUnavailableError
from app.schemas.base import MessageResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=MessageResponse,
    summary="Verifica se a API está online",
)
def health_check() -> MessageResponse:
    """Retorna um status simples da API.

    Este endpoint não consulta o banco porque ele serve para verificar se a
    aplicação FastAPI subiu corretamente. A checagem do PostgreSQL fica em uma
    rota separada para facilitar diagnóstico quando a API está online, mas o
    banco está indisponível.
    """

    return MessageResponse(message="API is running")


@router.get(
    "/health/db",
    response_model=MessageResponse,
    summary="Verifica se a API consegue acessar o banco de dados",
)
def database_health_check(db: Session = Depends(get_db)) -> MessageResponse:
    """Executa uma consulta mínima para validar a conexão com o PostgreSQL.

    Usar `SELECT 1` evita depender de tabelas específicas. Isso é útil porque o
    endpoint continua funcionando mesmo antes de aplicar todas as migrations.
    """

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError(
            message="Não foi possível conectar ao banco de dados."
        ) from exc

    return MessageResponse(message="Database connection is healthy")
