from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.user import User


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Categoria definida pelo usuário para classificar ativos.

    Categorias ajudam o dashboard a mostrar distribuição por classe, estratégia
    ou qualquer agrupamento que faça sentido para o usuário, como "Renda Fixa",
    "Ações Brasil", "Exterior" ou "Cripto".
    """

    __tablename__ = "categories"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship(back_populates="categories")
    assets: Mapped[list["Asset"]] = relationship(back_populates="category")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    )
