from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException, ErrorCode
from app.schemas import ErrorDetail, ErrorResponse


logger = logging.getLogger(__name__)


def _coerce_error_details(details: list[dict[str, Any]] | None) -> list[ErrorDetail]:
    """Converte detalhes livres em schemas padronizados.

    As exceções de domínio recebem detalhes como dicionários simples para não acoplar
    `core/exceptions.py` ao Pydantic. A conversão para schema acontece apenas na borda HTTP.
    """

    normalized_details: list[ErrorDetail] = []

    for detail in details or []:
        normalized_details.append(
            ErrorDetail(
                field=detail.get("field"),
                message=str(detail.get("message", "Erro na operação.")),
                type=str(detail.get("type", "application_error")),
            )
        )

    return normalized_details


def _build_error_response(
    *,
    request: Request,
    error_code: ErrorCode | str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    """Monta a resposta de erro no formato único da API.

    Centralizar esta montagem evita pequenas variações de contrato entre handlers,
    como `detail`, `errors`, `message` ou outros nomes inconsistentes.
    """

    response = ErrorResponse(
        error_code=str(error_code),
        message=message,
        details=details or [],
        path=request.url.path,
    )
    return response.model_dump(mode="json")


def _normalize_validation_errors(errors: list[dict[str, Any]]) -> list[ErrorDetail]:
    """Normaliza erros de validação do FastAPI/Pydantic para o contrato da API.

    O FastAPI informa a localização do erro em listas como `["body", "email"]`.
    Removemos o prefixo técnico `body` para que o frontend receba nomes de campos
    mais próximos dos formulários.
    """

    normalized_errors: list[ErrorDetail] = []

    for error in errors:
        location = error.get("loc", [])
        field_parts = [str(part) for part in location if part != "body"]
        field = ".".join(field_parts) if field_parts else None

        normalized_errors.append(
            ErrorDetail(
                field=field,
                message=str(error.get("msg", "Erro de validação.")),
                type=str(error.get("type", "validation_error")),
            )
        )

    return normalized_errors


def _error_code_from_http_status(status_code: int) -> ErrorCode:
    """Mapeia status HTTP comuns para códigos estáveis de aplicação."""

    status_map = {
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ErrorCode.RESOURCE_NOT_FOUND,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
        status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
    }
    return status_map.get(status_code, ErrorCode.HTTP_ERROR)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler para erros previstos de negócio.

    Estes erros são esperados e controlados, então não precisam ser registrados como
    exceções críticas. O status e o código vêm da própria exceção.
    """

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request=request,
            error_code=exc.error_code,
            message=exc.message,
            details=_coerce_error_details(exc.details),
        ),
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handler para erros de validação gerados automaticamente pelo FastAPI."""

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            request=request,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Dados inválidos na requisição.",
            details=_normalize_validation_errors(exc.errors()),
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handler para HTTPException e erros HTTP do Starlette/FastAPI.

    Erros como 404 também passam por aqui, permitindo manter o mesmo contrato para
    rotas inexistentes e para exceções HTTP levantadas explicitamente.
    """

    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "Erro HTTP tratado pela aplicação."
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request=request,
            error_code=_error_code_from_http_status(exc.status_code),
            message=message,
        ),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handler para falhas de banco não tratadas anteriormente.

    Registramos o erro real no log, mas retornamos uma mensagem segura para o cliente.
    Isso evita vazar detalhes de conexão, SQL ou estrutura interna do banco.
    """

    logger.exception("Erro de banco de dados não tratado: %s", exc)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=_build_error_response(
            request=request,
            error_code=ErrorCode.DATABASE_UNAVAILABLE,
            message="Banco de dados temporariamente indisponível.",
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler final para erros inesperados.

    Este handler é a última camada de proteção. Ele preserva uma resposta previsível
    para o frontend e registra detalhes no log para diagnóstico durante desenvolvimento
    e produção.
    """

    logger.exception("Erro inesperado não tratado: %s", exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            request=request,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Erro interno inesperado.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers globais da aplicação.

    Mantemos o registro em uma função para deixar o `main.py` pequeno e legível.
    Essa organização facilita a evolução para testes, observabilidade e logs
    estruturados sem espalhar configuração pela aplicação.
    """

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
