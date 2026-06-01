from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserRead


class TokenPayload(BaseModel):
    """Payload esperado dentro do access token JWT.

    O `sub` guarda o identificador do usuário como string. Nas dependências de
    autenticação das próximas etapas, esse valor será convertido para UUID e
    usado para buscar o usuário no banco.
    """

    sub: str
    exp: datetime
    iat: datetime
    token_type: str = "access"


class TokenResponse(BaseModel):
    """Resposta devolvida futuramente pelo endpoint de login.

    Manter esse contrato desde agora ajuda o frontend a saber que receberá um
    token no padrão Bearer, junto com o tempo de expiração em segundos.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)


class LoginRequest(BaseModel):
    """Payload de entrada para autenticação por e-mail e senha.

    O schema normaliza o e-mail antes de chegar ao service. Isso evita falhas de
    login por diferença de maiúsculas/minúsculas e mantém compatibilidade com o
    índice case-insensitive criado no banco.
    """

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normaliza o e-mail informado no login."""

        return str(value).strip().lower()


class RegisterResponse(BaseModel):
    """Resposta do fluxo de cadastro com usuário público e token.

    Retornar o token logo após cadastro permite que o frontend já direcione o
    usuário para a área logada sem exigir um segundo login manual.
    """

    user: UserRead
    token: TokenResponse
