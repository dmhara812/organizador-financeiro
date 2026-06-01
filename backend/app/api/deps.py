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

# O tokenUrl aponta para a rota que será criada na Etapa 6.4. Mesmo antes da
# rota existir, esta configuração já prepara o Swagger/OpenAPI para entender o
# fluxo Bearer Token das rotas protegidas.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
)

DbSessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_auth_service(db: DbSessionDep) -> AuthService:
    """Cria o service de autenticação para uso nas rotas.

    Centralizar a criação aqui evita que cada rota precise conhecer detalhes de
    sessão de banco ou instanciação do service. Isso também facilita testes,
    porque o FastAPI permite sobrescrever dependências em `app.dependency_overrides`.
    """

    return AuthService(db=db)


def get_current_user(token: TokenDep, db: DbSessionDep) -> User:
    """Retorna o usuário autenticado a partir do token JWT.

    O JWT carrega apenas o `sub`, que representa o ID do usuário. A consulta ao
    banco é necessária para garantir que o usuário ainda existe e para obter o
    estado atual da conta, como `is_active`.
    """

    token_payload = decode_access_token(token)
    user_id = _parse_user_id_from_token_subject(token_payload.sub)

    user_repository = UserRepository(db=db)
    user = user_repository.get_by_id(user_id)

    if user is None:
        # Não retornamos 404 aqui. Para autenticação, a resposta deve ser
        # genérica, evitando revelar se o token apontava para um usuário real.
        raise AuthenticationError(message="Credenciais inválidas.")

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Retorna o usuário autenticado apenas se a conta estiver ativa.

    Separar esta validação permite que fluxos futuros usem `get_current_user`
    diretamente quando fizer sentido, mas o padrão das rotas protegidas será
    exigir usuário ativo.
    """

    if not current_user.is_active:
        raise AuthorizationError(message="Usuário inativo.")

    return current_user


def require_current_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UUID:
    """Retorna somente o ID do usuário autenticado e ativo.

    Esse helper será útil em rotas que não precisam do objeto `User` completo,
    mas precisam aplicar filtros de ownership nos repositories e services.
    """

    return current_user.id


def _parse_user_id_from_token_subject(subject: str) -> UUID:
    """Converte o `sub` do token em UUID.

    Tokens malformados ou criados com `sub` inválido devem falhar como erro de
    autenticação, não como erro interno da aplicação.
    """

    try:
        return UUID(subject)
    except ValueError as exc:
        raise AuthenticationError(message="Credenciais inválidas.") from exc


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
CurrentUserIdDep = Annotated[UUID, Depends(require_current_user_id)]
