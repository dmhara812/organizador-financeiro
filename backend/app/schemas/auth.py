from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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
