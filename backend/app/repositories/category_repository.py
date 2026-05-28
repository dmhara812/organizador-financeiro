from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.repositories.base import BaseRepository
from app.repositories.query_utils import SortDirection, apply_order_by, paginate_select


class CategoryRepository(BaseRepository[Category]):
    """Repository específico para categorias de ativos.

    Categorias pertencem a um usuário. Por isso, os métodos principais recebem
    `user_id` e filtram por ownership desde a camada de consulta, reduzindo o
    risco de vazamento de dados entre contas.
    """

    _ALLOWED_SORT_FIELDS = {"name", "created_at", "updated_at"}

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=Category)

    def get_by_name(self, *, user_id: UUID, name: str) -> Category | None:
        """Busca uma categoria do usuário pelo nome de forma case-insensitive."""

        normalized_name = self._normalize_lookup_value(name)
        if not normalized_name:
            return None

        stmt = select(Category).where(
            Category.user_id == user_id,
            func.lower(Category.name) == normalized_name,
        )
        return self.db.execute(stmt).scalars().first()

    def name_exists(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_category_id: UUID | None = None,
    ) -> bool:
        """Verifica duplicidade de nome dentro das categorias do usuário.

        `exclude_category_id` será usado em updates para permitir que uma
        categoria mantenha o próprio nome sem ser considerada duplicada.
        """

        normalized_name = self._normalize_lookup_value(name)
        if not normalized_name:
            return False

        stmt = select(Category.id).where(
            Category.user_id == user_id,
            func.lower(Category.name) == normalized_name,
        )

        if exclude_category_id is not None:
            stmt = stmt.where(Category.id != exclude_category_id)

        return self.db.execute(stmt).first() is not None

    def list_by_user(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        search: str | None = None,
        sort_by: str | None = "name",
        sort_direction: SortDirection = "asc",
    ) -> tuple[list[Category], int]:
        """Lista categorias de um usuário com busca, ordenação e paginação.

        O retorno `(items, total)` será transformado em resposta paginada pelos
        services ou rotas futuras. Manter a montagem do schema fora daqui evita
        acoplar repository com camada de API.
        """

        stmt = select(Category).where(Category.user_id == user_id)

        normalized_search = self._normalize_lookup_value(search) if search else None
        if normalized_search:
            search_pattern = f"%{normalized_search}%"
            stmt = stmt.where(
                or_(
                    func.lower(Category.name).like(search_pattern),
                    func.lower(Category.description).like(search_pattern),
                )
            )

        stmt = apply_order_by(
            stmt,
            model=Category,
            sort_by=sort_by,
            sort_direction=sort_direction,
            allowed_fields=self._ALLOWED_SORT_FIELDS,
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    @staticmethod
    def _normalize_lookup_value(value: str) -> str:
        """Normaliza texto usado em buscas e verificações de duplicidade."""

        return value.strip().lower()
