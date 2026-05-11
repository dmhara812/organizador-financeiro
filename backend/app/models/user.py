from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.asset_price import AssetPrice
    from app.models.brokerage import Brokerage
    from app.models.category import Category
    from app.models.transaction import Transaction


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Usuário autenticável do sistema.

    A senha será armazenada somente como hash. A autenticação JWT será criada
    na Etapa 6, mas o model já deixa os campos necessários preparados.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    categories: Mapped[list["Category"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    brokerages: Mapped[list["Brokerage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    asset_prices: Mapped[list["AssetPrice"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_users_email_lower", func.lower(email), unique=True),)
