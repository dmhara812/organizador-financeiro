from __future__ import annotations

from enum import StrEnum

from fastapi import status


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
    """Classe base para erros esperados da aplicação."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "APP_ERROR"
    default_message = "Erro na aplicação."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


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


class ResourceNotFoundError(AppException):
    """Erro usado quando um recurso não foi encontrado.

    Esse nome é usado pelos services para deixar claro que a falha aconteceu
    ao buscar uma entidade do domínio, como ativo, categoria, corretora ou usuário.
    """

    def __init__(
        self,
        message: str = "Recurso não encontrado.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationAppError(AppException):
    """Erro usado quando uma regra de validação da aplicação é violada.

    Esse erro representa falhas de regra de negócio, como tentar vender mais
    ativos do que o usuário possui ou criar registros duplicados.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )
