from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import AppBaseModel, BaseReadSchema
from app.schemas.enums import AssetType
from app.schemas.validators import (
    normalize_optional_upper,
    normalize_required_currency_code,
    normalize_symbol,
    validate_optional_isin,
)


class AssetBase(AppBaseModel):
    """Campos principais de um ativo financeiro.

    A posição do ativo não aparece aqui porque será calculada a partir das
    movimentações, mantendo o histórico como fonte da verdade.
    """

    category_id: UUID | None = None
    symbol: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=2, max_length=160)
    asset_type: AssetType
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    exchange: str | None = Field(default=None, max_length=40)
    isin: str | None = Field(default=None, min_length=12, max_length=12)
    is_active: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_asset_symbol(cls, value: str) -> str:
        """Evita duplicidade visual entre símbolos com caixas diferentes."""

        return normalize_symbol(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Mantém moeda em caixa alta e com três letras."""

        return normalize_required_currency_code(value)

    @field_validator("exchange")
    @classmethod
    def normalize_exchange(cls, value: str | None) -> str | None:
        """Padroniza bolsa em caixa alta quando informada."""

        return normalize_optional_upper(value)

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, value: str | None) -> str | None:
        """Valida ISIN opcional para preparar integrações futuras."""

        return validate_optional_isin(value)


class AssetCreate(AssetBase):
    """Payload de criação de ativo.

    `user_id` será extraído do usuário autenticado, não do corpo da requisição.
    """


class AssetUpdate(AppBaseModel):
    """Payload de atualização parcial de ativo.

    Services futuros deverão usar `model_dump(exclude_unset=True)` para
    diferenciar campos omitidos de campos enviados explicitamente como nulos.
    """

    category_id: UUID | None = None
    symbol: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    asset_type: AssetType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    exchange: str | None = Field(default=None, max_length=40)
    isin: str | None = Field(default=None, min_length=12, max_length=12)
    is_active: bool | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_asset_symbol(cls, value: str | None) -> str | None:
        """Aplica normalização apenas quando o campo é enviado."""

        if value is None:
            return None
        return normalize_symbol(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Permite atualização parcial sem perder a validação de moeda."""

        if value is None:
            return None
        return normalize_required_currency_code(value)

    @field_validator("exchange")
    @classmethod
    def normalize_exchange(cls, value: str | None) -> str | None:
        """Padroniza bolsa quando enviada no update."""

        return normalize_optional_upper(value)

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, value: str | None) -> str | None:
        """Aplica a mesma regra de ISIN usada na criação."""

        return validate_optional_isin(value)


class AssetRead(BaseReadSchema):
    """Resposta de ativo para listagens, detalhes e filtros."""

    category_id: UUID | None
    symbol: str
    name: str
    asset_type: AssetType
    currency: str
    exchange: str | None
    isin: str | None
    is_active: bool
