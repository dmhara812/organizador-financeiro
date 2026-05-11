from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PriceSource, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.user import User


class AssetPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Preço histórico de um ativo em uma data.

    Esta tabela permite calcular valor de mercado e histórico do patrimônio sem
    depender de integração externa na primeira versão. A origem do preço deixa o
    modelo pronto para importação CSV e APIs de cotação depois.
    """

    __tablename__ = "asset_prices"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    source: Mapped[PriceSource] = mapped_column(
        SQLAlchemyEnum(
            PriceSource,
            name="price_source",
            values_callable=enum_values,
        ),
        nullable=False,
        default=PriceSource.MANUAL,
    )

    user: Mapped["User"] = relationship(back_populates="asset_prices")
    asset: Mapped["Asset"] = relationship(back_populates="prices")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "asset_id",
            "price_date",
            name="uq_asset_prices_user_asset_date",
        ),
        CheckConstraint("price > 0", name="ck_asset_prices_price_positive"),
        CheckConstraint(
            "char_length(currency) = 3", name="ck_asset_prices_currency_length"
        ),
        Index("ix_asset_prices_asset_date", "asset_id", "price_date"),
    )
