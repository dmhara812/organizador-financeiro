from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.base import AppBaseModel, BaseReadSchema
from app.schemas.enums import TransactionType
from app.schemas.validators import normalize_required_currency_code

_TRADE_TYPES = {TransactionType.BUY, TransactionType.SELL}
_CASH_ONLY_TYPES = {TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAWAL}
_INCOME_WITH_REQUIRED_ASSET_TYPES = {TransactionType.DIVIDEND}


class TransactionBase(AppBaseModel):
    """Campos principais de movimentação financeira.

    Movimentações são a fonte da verdade do projeto. Por isso o contrato mantém
    valores brutos, taxas, impostos e valor líquido explícitos.
    """

    asset_id: UUID | None = None
    brokerage_id: UUID | None = None
    transaction_type: TransactionType
    occurred_at: datetime
    quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=24, decimal_places=8
    )
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=8
    )
    gross_amount: Decimal = Field(..., ge=0, max_digits=20, decimal_places=2)
    fee_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=20, decimal_places=2
    )
    tax_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=20, decimal_places=2
    )
    net_amount: Decimal = Field(..., ge=0, max_digits=20, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=1000)
    external_reference: str | None = Field(default=None, max_length=120)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Padroniza moeda antes de services e repositories processarem valores."""

        return normalize_required_currency_code(value)


class TransactionCreate(TransactionBase):
    """Payload de criação de movimentação.

    Validações que dependem de banco, como ownership e posição disponível,
    ficarão nos services para manter separação de responsabilidades.
    """

    @model_validator(mode="after")
    def validate_transaction_shape(self) -> Self:
        """Valida combinações mínimas por tipo de movimentação."""

        if self.transaction_type in _TRADE_TYPES:
            if self.asset_id is None:
                raise ValueError("Compras e vendas exigem asset_id.")
            if self.quantity is None:
                raise ValueError("Compras e vendas exigem quantity.")
            if self.unit_price is None:
                raise ValueError("Compras e vendas exigem unit_price.")

        if self.transaction_type in _CASH_ONLY_TYPES:
            if self.asset_id is not None:
                raise ValueError("Aportes e retiradas de caixa não devem ter asset_id.")
            if self.quantity is not None or self.unit_price is not None:
                raise ValueError(
                    "Aportes e retiradas de caixa não devem ter quantity ou unit_price."
                )

        if (
            self.transaction_type in _INCOME_WITH_REQUIRED_ASSET_TYPES
            and self.asset_id is None
        ):
            raise ValueError("Dividendos devem estar associados a um ativo.")

        return self


class TransactionUpdate(AppBaseModel):
    """Payload de atualização parcial de movimentação."""

    asset_id: UUID | None = None
    brokerage_id: UUID | None = None
    transaction_type: TransactionType | None = None
    occurred_at: datetime | None = None
    quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=24, decimal_places=8
    )
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=8
    )
    gross_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=2
    )
    fee_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=2
    )
    tax_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=2
    )
    net_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=2
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=1000)
    external_reference: str | None = Field(default=None, max_length=120)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Mantém updates parciais compatíveis com a regra de moeda."""

        if value is None:
            return None
        return normalize_required_currency_code(value)


class TransactionRead(BaseReadSchema):
    """Resposta de movimentação sem expor `user_id`."""

    asset_id: UUID | None
    brokerage_id: UUID | None
    transaction_type: TransactionType
    occurred_at: datetime
    quantity: Decimal | None
    unit_price: Decimal | None
    gross_amount: Decimal
    fee_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    currency: str
    notes: str | None
    external_reference: str | None
