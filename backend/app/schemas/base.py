from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Base única para os schemas Pydantic da aplicação.

    `from_attributes=True` permite montar respostas a partir de objetos
    SQLAlchemy sem acoplar rotas aos models. `str_strip_whitespace=True`
    remove espaços desnecessários em entradas textuais, reduzindo validações
    repetidas nos schemas específicos das próximas etapas.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class BaseSchema(AppBaseModel):
    """Alias de compatibilidade para etapas que importam BaseSchema."""


class IDSchema(AppBaseModel):
    """Contrato reutilizável para entidades expostas pela API com UUID."""

    id: UUID


class TimestampSchema(AppBaseModel):
    """Contrato reutilizável para campos de auditoria básica."""

    created_at: datetime
    updated_at: datetime


class BaseReadSchema(IDSchema, TimestampSchema):
    """Base para schemas de leitura de entidades persistidas."""


class MessageResponse(BaseModel):
    """Resposta simples para endpoints que só precisam retornar uma mensagem.

    Usamos um schema próprio, em vez de retornar `dict` diretamente, para manter
    o contrato da API explícito no Swagger/OpenAPI e facilitar o consumo pelo
    frontend.
    """

    message: str
