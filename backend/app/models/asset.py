from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AssetType, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset_price import AssetPrice
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ativo financeiro acompanhado pelo usuário.

    O ativo representa o instrumento negociado ou acompanhado. A posição não é
    salva aqui porque será calculada a partir de `transactions`, mantendo as
    movimentações como fonte da verdade.
    """

    __tablename__ = "assets"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        SQLAlchemyEnum(
            AssetType,
            name="asset_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    exchange: Mapped[str | None] = mapped_column(String(40), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="assets")
    category: Mapped["Category | None"] = relationship(back_populates="assets")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="asset")
    prices: Mapped[list["AssetPrice"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "symbol",
            "asset_type",
            name="uq_assets_user_symbol_type",
        ),
        Index("ix_assets_user_type", "user_id", "asset_type"),
    )
