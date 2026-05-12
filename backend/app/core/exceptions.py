from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Códigos estáveis de erro usados pelo backend e consumidos pelo frontend.

    Usamos códigos em inglês e em caixa alta para manter um contrato estável de API.
    A mensagem pode mudar para melhorar clareza, mas o código deve permanecer previsível
    para que o frontend consiga tomar decisões, como redirecionar em erro de autenticação.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppException(Exception):
    """Exceção base para erros previstos da aplicação.

    Services e repositories devem lançar subclasses desta exceção quando encontrarem
    uma regra de negócio inválida. A transformação para HTTP fica centralizada nos
    handlers globais, evitando que as camadas internas dependam diretamente do FastAPI.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_code: ErrorCode,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []


class ValidationAppError(AppException):
    """Erro usado para validações de negócio que não são capturadas pelo Pydantic.

    Exemplo futuro: impedir venda de uma quantidade maior do que a posição disponível
    para determinado ativo.
    """

    def __init__(
        self,
        message: str = "Dados inválidos para a operação solicitada.",
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
        )


class UnauthorizedError(AppException):
    """Erro para chamadas sem credenciais válidas."""

    def __init__(self, message: str = "Autenticação necessária.") -> None:
        super().__init__(
            message,
            status_code=401,
            error_code=ErrorCode.UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    """Erro para usuário autenticado tentando acessar recurso sem permissão.

    Este erro será importante quando validarmos ownership, impedindo que um usuário
    acesse ativos, categorias ou movimentações pertencentes a outro usuário.
    """

    def __init__(
        self, message: str = "Você não tem permissão para acessar este recurso."
    ) -> None:
        super().__init__(
            message,
            status_code=403,
            error_code=ErrorCode.FORBIDDEN,
        )


class ResourceNotFoundError(AppException):
    """Erro para recursos inexistentes ou inacessíveis pelo usuário atual."""

    def __init__(self, resource_name: str = "Recurso") -> None:
        super().__init__(
            f"{resource_name} não encontrado.",
            status_code=404,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )


class ConflictError(AppException):
    """Erro para conflitos de unicidade ou estado inválido.

    Exemplo futuro: tentar cadastrar uma categoria com nome já usado pelo mesmo usuário.
    """

    def __init__(
        self,
        message: str = "A operação não pôde ser concluída por conflito com o estado atual.",
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=409,
            error_code=ErrorCode.CONFLICT,
            details=details,
        )


class DatabaseUnavailableError(AppException):
    """Erro genérico para falhas de banco de dados.

    Não incluímos detalhes técnicos na mensagem porque respostas HTTP não devem vazar
    SQL, nomes internos de tabelas, credenciais ou stack traces.
    """

    def __init__(self) -> None:
        super().__init__(
            "Banco de dados temporariamente indisponível.",
            status_code=503,
            error_code=ErrorCode.DATABASE_UNAVAILABLE,
        )
