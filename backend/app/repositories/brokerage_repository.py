from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.brokerage import Brokerage
from app.repositories.base import BaseRepository
from app.repositories.query_utils import SortDirection, apply_order_by, paginate_select


class BrokerageRepository(BaseRepository[Brokerage]):
    """Repository específico para corretoras e instituições financeiras.

    Corretoras pertencem a um usuário e serão usadas para filtros de
    movimentações, relatórios por instituição e telas de gestão. As consultas
    sempre filtram por `user_id` para preservar ownership.
    """

    _ALLOWED_SORT_FIELDS = {"name", "country", "created_at", "updated_at"}

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=Brokerage)

    def get_by_name(self, *, user_id: UUID, name: str) -> Brokerage | None:
        """Busca uma corretora do usuário pelo nome de forma case-insensitive."""

        normalized_name = self._normalize_lookup_value(name)
        if not normalized_name:
            return None

        stmt = select(Brokerage).where(
            Brokerage.user_id == user_id,
            func.lower(Brokerage.name) == normalized_name,
        )
        return self.db.execute(stmt).scalars().first()

    def name_exists(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_brokerage_id: UUID | None = None,
    ) -> bool:
        """Verifica duplicidade de nome dentro das corretoras do usuário."""

        normalized_name = self._normalize_lookup_value(name)
        if not normalized_name:
            return False

        stmt = select(Brokerage.id).where(
            Brokerage.user_id == user_id,
            func.lower(Brokerage.name) == normalized_name,
        )

        if exclude_brokerage_id is not None:
            stmt = stmt.where(Brokerage.id != exclude_brokerage_id)

        return self.db.execute(stmt).first() is not None

    def list_by_user(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        search: str | None = None,
        country: str | None = None,
        sort_by: str | None = "name",
        sort_direction: SortDirection = "asc",
    ) -> tuple[list[Brokerage], int]:
        """Lista corretoras do usuário com filtros e paginação.

        O filtro de país é opcional e usa código de duas letras. A normalização
        defensiva no repository evita resultados inconsistentes caso o service
        chame o método com letras minúsculas.
        """

        stmt = select(Brokerage).where(Brokerage.user_id == user_id)

        normalized_country = self._normalize_country(country)
        if normalized_country:
            stmt = stmt.where(Brokerage.country == normalized_country)

        normalized_search = self._normalize_lookup_value(search) if search else None
        if normalized_search:
            search_pattern = f"%{normalized_search}%"
            stmt = stmt.where(
                or_(
                    func.lower(Brokerage.name).like(search_pattern),
                    func.lower(Brokerage.country).like(search_pattern),
                    func.lower(Brokerage.website).like(search_pattern),
                )
            )

        stmt = apply_order_by(
            stmt,
            model=Brokerage,
            sort_by=sort_by,
            sort_direction=sort_direction,
            allowed_fields=self._ALLOWED_SORT_FIELDS,
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    @staticmethod
    def _normalize_lookup_value(value: str) -> str:
        """Normaliza texto usado em buscas e verificações de duplicidade."""

        return value.strip().lower()

    @staticmethod
    def _normalize_country(country: str | None) -> str | None:
        """Normaliza código de país opcional para duas letras maiúsculas."""

        if country is None:
            return None

        normalized_country = country.strip().upper()
        return normalized_country or None
