from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.base import AppBaseModel, BaseReadSchema
from app.schemas.validators import validate_optional_country_code


class BrokerageBase(AppBaseModel):
    """Campos principais de corretora ou instituição financeira."""

    name: str = Field(..., min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    website: str | None = Field(default=None, max_length=255)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        """Padroniza país em duas letras para filtros consistentes."""

        return validate_optional_country_code(value)


class BrokerageCreate(BrokerageBase):
    """Payload de criação de corretora.

    O usuário dono será definido pelo JWT na etapa de autenticação.
    """


class BrokerageUpdate(AppBaseModel):
    """Payload de atualização parcial de corretora."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    website: str | None = Field(default=None, max_length=255)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        """Aplica a mesma normalização de país usada na criação."""

        return validate_optional_country_code(value)


class BrokerageRead(BaseReadSchema):
    """Resposta de corretora usada nas telas de gestão e filtros."""

    name: str
    country: str | None
    website: str | None
