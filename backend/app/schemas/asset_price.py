from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import AppBaseModel, BaseReadSchema
from app.schemas.enums import PriceSource
from app.schemas.validators import normalize_required_currency_code


class AssetPriceBase(AppBaseModel):
    """Campos principais de preço histórico de ativo."""

    asset_id: UUID
    price_date: date
    price: Decimal = Field(..., gt=0, max_digits=20, decimal_places=8)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    source: PriceSource = PriceSource.MANUAL

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Padroniza moeda do preço para agregações futuras."""

        return normalize_required_currency_code(value)


class AssetPriceCreate(AssetPriceBase):
    """Payload de criação de preço histórico."""


class AssetPriceUpdate(AppBaseModel):
    """Payload de atualização parcial de preço histórico."""

    price_date: date | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=8)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source: PriceSource | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Permite update parcial preservando a regra de moeda."""

        if value is None:
            return None
        return normalize_required_currency_code(value)


class AssetPriceRead(BaseReadSchema):
    """Resposta de preço histórico de ativo."""

    asset_id: UUID
    price_date: date
    price: Decimal
    currency: str
    source: PriceSource
