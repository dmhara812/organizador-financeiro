from __future__ import annotations

from fastapi import status

from enum import StrEnum


class ErrorCode(StrEnum):
    """Códigos internos de erro usados nas respostas padronizadas da API.

    Manter os códigos em um enum evita strings soltas espalhadas pelo backend e
    reduz erros de digitação em handlers, services e rotas.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppException(Exception):
    """Exceção base da aplicação.

    Concentrar os erros de domínio em uma classe base permite que o handler
    global transforme falhas esperadas em respostas padronizadas para o frontend.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(AppException):
    """Erro usado quando uma regra de negócio é violada."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class NotFoundError(AppException):
    """Erro usado quando um recurso esperado não foi encontrado."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(AppException):
    """Erro usado quando uma operação viola unicidade ou estado já existente."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class AuthenticationError(AppException):
    """Erro usado quando credenciais ou tokens são inválidos.

    A mensagem deve ser genérica para não revelar se o e-mail existe, se a senha
    está errada ou se o token falhou por expiração/assinatura.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"


class AuthorizationError(AppException):
    """Erro usado quando o usuário autenticado não pode acessar um recurso."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_ERROR"


class DatabaseUnavailableError(AppException):
    """Erro usado quando a aplicação não consegue acessar o banco de dados."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATABASE_UNAVAILABLE"
