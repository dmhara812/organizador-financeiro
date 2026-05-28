from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AssetType
from app.repositories.base import BaseRepository
from app.repositories.query_utils import SortDirection, apply_order_by, paginate_select


class AssetRepository(BaseRepository[Asset]):
    """Repository específico para consultas de ativos financeiros.

    Ativos sempre pertencem a um usuário. Por isso, os métodos principais
    exigem `user_id` e já preparam a regra de ownership que será reforçada nos
    services e nas rotas protegidas.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=Asset)

    def get_by_user_and_symbol(self, user_id: UUID, symbol: str) -> Asset | None:
        """Busca um ativo pelo símbolo dentro do escopo de um usuário.

        A busca é case-insensitive para evitar duplicidades lógicas como
        `PETR4` e `petr4`. A normalização final também será reforçada pelos
        schemas e services.
        """

        normalized_symbol = self._normalize_symbol(symbol)
        if not normalized_symbol:
            return None

        stmt = select(Asset).where(
            Asset.user_id == user_id,
            func.lower(Asset.symbol) == normalized_symbol,
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def symbol_exists(
        self,
        user_id: UUID,
        symbol: str,
        *,
        exclude_asset_id: UUID | None = None,
    ) -> bool:
        """Verifica se um símbolo já foi cadastrado pelo usuário.

        `exclude_asset_id` será útil em atualizações, permitindo que o ativo
        atual mantenha o próprio símbolo sem gerar falso positivo.
        """

        normalized_symbol = self._normalize_symbol(symbol)
        if not normalized_symbol:
            return False

        stmt = select(Asset.id).where(
            Asset.user_id == user_id,
            func.lower(Asset.symbol) == normalized_symbol,
        )

        if exclude_asset_id is not None:
            stmt = stmt.where(Asset.id != exclude_asset_id)

        return self.db.execute(stmt).first() is not None

    def list_by_user(
        self,
        user_id: UUID,
        *,
        page: int,
        size: int,
        asset_type: AssetType | None = None,
        category_id: UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str | None = "symbol",
        sort_direction: SortDirection = "asc",
    ) -> tuple[list[Asset], int]:
        """Lista ativos de um usuário com filtros e paginação.

        A query ainda não calcula posição ou valor de mercado. Esses cálculos
        dependem de movimentações e preços e serão implementados nos services.
        """

        stmt = select(Asset).where(Asset.user_id == user_id)

        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type)

        if category_id is not None:
            stmt = stmt.where(Asset.category_id == category_id)

        if is_active is not None:
            stmt = stmt.where(Asset.is_active == is_active)

        normalized_search = self._normalize_search(search)
        if normalized_search:
            search_pattern = f"%{normalized_search}%"
            stmt = stmt.where(
                or_(
                    func.lower(Asset.symbol).like(search_pattern),
                    func.lower(Asset.name).like(search_pattern),
                    func.lower(Asset.currency).like(search_pattern),
                    func.lower(Asset.exchange).like(search_pattern),
                    func.lower(Asset.isin).like(search_pattern),
                )
            )

        stmt = apply_order_by(
            stmt,
            model=Asset,
            sort_by=sort_by,
            sort_direction=sort_direction,
            allowed_fields={
                "symbol",
                "name",
                "asset_type",
                "currency",
                "exchange",
                "created_at",
                "updated_at",
            },
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    def list_active_by_user(self, user_id: UUID) -> list[Asset]:
        """Lista ativos ativos de um usuário sem paginação.

        Este método será útil para telas de seleção, como cadastro de
        movimentação. Para listagens públicas maiores, prefira `list_by_user`.
        """

        stmt = (
            select(Asset)
            .where(
                Asset.user_id == user_id,
                Asset.is_active.is_(True),
            )
            .order_by(Asset.symbol.asc())
        )

        return list(self.db.execute(stmt).scalars().all())

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normaliza símbolo para comparação case-insensitive."""

        return symbol.strip().lower()

    @staticmethod
    def _normalize_search(search: str | None) -> str | None:
        """Normaliza termo de busca textual."""

        if search is None:
            return None

        normalized_search = search.strip().lower()
        return normalized_search or None
