from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.base import AppBaseModel, BaseReadSchema
from app.schemas.validators import validate_optional_hex_color


class CategoryBase(AppBaseModel):
    """Campos principais de uma categoria de ativos."""

    name: str = Field(..., min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=20)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        """Mantém cores em formato previsível para gráficos futuros."""

        return validate_optional_hex_color(value)


class CategoryCreate(CategoryBase):
    """Payload de criação de categoria.

    `user_id` não vem do cliente; ele será obtido do usuário autenticado.
    """


class CategoryUpdate(AppBaseModel):
    """Payload de atualização parcial de categoria."""

    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=20)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        """Aplica a mesma validação de cor usada na criação."""

        return validate_optional_hex_color(value)


class CategoryRead(BaseReadSchema):
    """Resposta de categoria sem expor `user_id`."""

    name: str
    description: str | None
    color: str | None
