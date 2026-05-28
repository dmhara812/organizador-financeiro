from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError as PydanticValidationError
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.schemas.auth import TokenPayload

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Gera hash seguro para a senha do usuário.

    Senhas nunca devem ser armazenadas em texto puro. O hash gerado por esta
    função será persistido no campo `hashed_password` do usuário.
    """

    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara uma senha em texto puro com o hash salvo no banco.

    A verificação precisa ser centralizada para que login, testes e futuras
    trocas de algoritmo continuem usando o mesmo ponto de manutenção.
    """

    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Cria um access token JWT assinado.

    O `subject` representa o usuário autenticado. Usamos string para manter o
    payload simples e compatível com JSON; nas próximas etapas, esse valor será
    convertido para UUID quando formos carregar o usuário atual.
    """

    settings = get_settings()
    now = datetime.now(UTC)
    expire_at = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire_at,
        "token_type": "access",
    }

    if additional_claims:
        # Claims extras ficam restritas a usos explícitos. Isso evita misturar
        # dados sensíveis ou grandes demais no token por acidente.
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    """Decodifica e valida um access token JWT.

    A função converte falhas da biblioteca JWT e falhas de validação Pydantic em
    `AuthenticationError`, mantendo uma resposta consistente para o frontend.
    """

    settings = get_settings()

    try:
        decoded_payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        token_payload = TokenPayload.model_validate(decoded_payload)
    except (InvalidTokenError, PydanticValidationError) as exc:
        raise AuthenticationError(message="Credenciais inválidas.") from exc

    if token_payload.token_type != "access":
        raise AuthenticationError(message="Credenciais inválidas.")

    return token_payload
