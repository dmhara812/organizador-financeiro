from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class Brokerage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Corretora ou instituição onde uma movimentação acontece.

    Manter corretoras como entidade separada permite filtrar movimentações,
    comparar concentração por instituição e evoluir para relatórios de custódia
    no futuro.
    """

    __tablename__ = "brokerages"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="brokerages")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="brokerage")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_brokerages_user_name"),
    )
