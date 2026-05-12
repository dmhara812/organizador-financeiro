from __future__ import annotations

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.enums import AssetType, PriceSource, TransactionType
from app.schemas.pagination import PaginationParams
from app.schemas.validators import (
    normalize_optional_currency_code,
    normalize_optional_symbol,
    validate_optional_country_code,
)


class CategoryFilters(PaginationParams):
    """Filtros de listagem de categorias."""

    search: str | None = Field(default=None, min_length=1, max_length=80)


class BrokerageFilters(PaginationParams):
    """Filtros de listagem de corretoras."""

    search: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        """Padroniza país para filtros por corretora."""

        return validate_optional_country_code(value)


class AssetFilters(PaginationParams):
    """Filtros de listagem de ativos."""

    search: str | None = Field(default=None, min_length=1, max_length=160)
    symbol: str | None = Field(default=None, min_length=1, max_length=30)
    asset_type: AssetType | None = None
    category_id: UUID | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol_filter(cls, value: str | None) -> str | None:
        """Permite busca por ticker sem depender da caixa digitada pelo usuário."""

        return normalize_optional_symbol(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Padroniza moeda usada em filtros de ativos."""

        return normalize_optional_currency_code(value)


class TransactionFilters(PaginationParams):
    """Filtros de listagem de movimentações."""

    asset_id: UUID | None = None
    brokerage_id: UUID | None = None
    transaction_type: TransactionType | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    external_reference: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Padroniza moeda usada em filtros de movimentações."""

        return normalize_optional_currency_code(value)

    @model_validator(mode="after")
    def validate_datetime_range(self) -> Self:
        """Evita consultas com intervalo temporal invertido."""

        if (
            self.occurred_from is not None
            and self.occurred_to is not None
            and self.occurred_from > self.occurred_to
        ):
            raise ValueError("occurred_from não pode ser maior que occurred_to.")
        return self


class AssetPriceFilters(PaginationParams):
    """Filtros de listagem de preços históricos."""

    asset_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    source: PriceSource | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Padroniza moeda usada em filtros de preços."""

        return normalize_optional_currency_code(value)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        """Garante que o início do intervalo não seja posterior ao fim."""

        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from não pode ser maior que date_to.")
        return self
