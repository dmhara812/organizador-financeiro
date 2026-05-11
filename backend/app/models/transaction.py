from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TransactionType, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.brokerage import Brokerage
    from app.models.user import User


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Movimentação financeira do usuário.

    Esta é a tabela central do domínio. Compras, vendas, rendimentos, taxas e
    aportes ficam no mesmo histórico para que posição, patrimônio e evolução
    sejam derivados de uma fonte única e auditável.
    """

    __tablename__ = "transactions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    brokerage_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("brokerages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLAlchemyEnum(
            TransactionType,
            name="transaction_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, default=0
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")
    asset: Mapped["Asset | None"] = relationship(back_populates="transactions")
    brokerage: Mapped["Brokerage | None"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_transactions_quantity_positive"
        ),
        CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0",
            name="ck_transactions_unit_price_non_negative",
        ),
        CheckConstraint(
            "gross_amount >= 0", name="ck_transactions_gross_amount_non_negative"
        ),
        CheckConstraint(
            "fee_amount >= 0", name="ck_transactions_fee_amount_non_negative"
        ),
        CheckConstraint(
            "tax_amount >= 0", name="ck_transactions_tax_amount_non_negative"
        ),
        CheckConstraint(
            "net_amount >= 0", name="ck_transactions_net_amount_non_negative"
        ),
        CheckConstraint(
            "char_length(currency) = 3", name="ck_transactions_currency_length"
        ),
        Index("ix_transactions_user_occurred_at", "user_id", "occurred_at"),
        Index("ix_transactions_user_type", "user_id", "transaction_type"),
        Index("ix_transactions_asset_occurred_at", "asset_id", "occurred_at"),
    )
