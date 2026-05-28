from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.asset_price import AssetPrice
from app.models.enums import PriceSource
from app.repositories.base import BaseRepository
from app.repositories.query_utils import SortDirection, apply_order_by, paginate_select


class AssetPriceRepository(BaseRepository[AssetPrice]):
    """Repository específico para consultas de preços históricos.

    Preços são usados para estimar valor de mercado dos ativos. Eles ficam em um
    repository próprio porque têm regras de consulta diferentes de movimentações.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=AssetPrice)

    def get_by_asset_and_date(
        self,
        user_id: UUID,
        asset_id: UUID,
        price_date: date,
    ) -> AssetPrice | None:
        """Busca o preço de um ativo em uma data específica.

        A consulta inclui `user_id` para garantir ownership mesmo quando o
        `asset_id` é conhecido.
        """

        stmt = select(AssetPrice).where(
            AssetPrice.user_id == user_id,
            AssetPrice.asset_id == asset_id,
            AssetPrice.price_date == price_date,
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_asset(
        self,
        user_id: UUID,
        asset_id: UUID,
        *,
        page: int,
        size: int,
        price_from: date | None = None,
        price_to: date | None = None,
        source: PriceSource | None = None,
        sort_by: str | None = "price_date",
        sort_direction: SortDirection = "desc",
    ) -> tuple[list[AssetPrice], int]:
        """Lista histórico de preços de um ativo com filtros de período."""

        stmt = select(AssetPrice).where(
            AssetPrice.user_id == user_id,
            AssetPrice.asset_id == asset_id,
        )

        if price_from is not None:
            stmt = stmt.where(AssetPrice.price_date >= price_from)

        if price_to is not None:
            stmt = stmt.where(AssetPrice.price_date <= price_to)

        if source is not None:
            stmt = stmt.where(AssetPrice.source == source)

        stmt = apply_order_by(
            stmt,
            model=AssetPrice,
            sort_by=sort_by,
            sort_direction=sort_direction,
            allowed_fields={
                "price_date",
                "price",
                "currency",
                "source",
                "created_at",
                "updated_at",
            },
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    def get_latest_by_asset(
        self,
        user_id: UUID,
        asset_id: UUID,
    ) -> AssetPrice | None:
        """Busca o preço mais recente de um ativo.

        Essa consulta será usada futuramente para calcular valor de mercado sem
        precisar carregar todo o histórico de preços.
        """

        stmt = (
            select(AssetPrice)
            .where(
                AssetPrice.user_id == user_id,
                AssetPrice.asset_id == asset_id,
            )
            .order_by(AssetPrice.price_date.desc(), AssetPrice.created_at.desc())
            .limit(1)
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def list_latest_by_user(self, user_id: UUID) -> list[AssetPrice]:
        """Lista o preço mais recente de cada ativo do usuário.

        A subquery encontra a data mais recente por ativo. A query externa busca
        os registros completos de preço nessa data. Esse formato evita fazer uma
        consulta separada para cada ativo.
        """

        latest_dates = (
            select(
                AssetPrice.asset_id.label("asset_id"),
                func.max(AssetPrice.price_date).label("latest_date"),
            )
            .where(AssetPrice.user_id == user_id)
            .group_by(AssetPrice.asset_id)
            .subquery()
        )

        stmt = (
            select(AssetPrice)
            .join(
                latest_dates,
                and_(
                    AssetPrice.asset_id == latest_dates.c.asset_id,
                    AssetPrice.price_date == latest_dates.c.latest_date,
                ),
            )
            .where(AssetPrice.user_id == user_id)
            .order_by(AssetPrice.asset_id.asc())
        )

        return list(self.db.execute(stmt).scalars().all())
