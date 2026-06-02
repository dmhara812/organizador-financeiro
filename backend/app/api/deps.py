from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

settings = get_settings()

# `tokenUrl` aponta para a rota form-compatible criada nesta etapa.
# Isso permite que o Swagger use o fluxo OAuth2 Password para autenticar testes
# manuais em rotas protegidas.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token",
)

DbSessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_auth_service(db: DbSessionDep) -> AuthService:
    """Cria o service de autenticação para uso nas rotas.

    Centralizar a instanciação em uma dependência facilita testes futuros com
    `app.dependency_overrides` e mantém as rotas sem detalhes de sessão de banco.
    """

    return AuthService(db=db)


def get_current_user(token: TokenDep, db: DbSessionDep) -> User:
    """Retorna o usuário autenticado a partir do token JWT."""

    token_payload = decode_access_token(token)
    user_id = _parse_user_id_from_token_subject(token_payload.sub)

    user_repository = UserRepository(db=db)
    user = user_repository.get_by_id(user_id)

    if user is None:
        # Falhas de autenticação devem ser genéricas para não revelar se o token
        # apontava para um usuário que já existiu ou não.
        raise AuthenticationError(message="Token inválido ou expirado.")

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Retorna o usuário autenticado apenas se a conta estiver ativa."""

    if not current_user.is_active:
        raise AuthorizationError(message="Usuário inativo.")

    return current_user


def require_current_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UUID:
    """Retorna somente o ID do usuário autenticado e ativo.

    Esse helper será usado em rotas que precisam aplicar ownership, mas não
    precisam do objeto `User` completo.
    """

    return current_user.id


def _parse_user_id_from_token_subject(subject: str) -> UUID:
    """Converte o `sub` do token em UUID.

    Tokens malformados devem falhar como erro de autenticação, não como erro
    interno da aplicação.
    """

    try:
        return UUID(subject)
    except ValueError as exc:
        raise AuthenticationError(message="Token inválido ou expirado.") from exc


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
CurrentUserIdDep = Annotated[UUID, Depends(require_current_user_id)]
