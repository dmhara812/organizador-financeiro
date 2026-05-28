from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.enums import PriceSource
from app.repositories import AssetPriceRepository, AssetRepository, SortDirection
from app.schemas.asset_price import AssetPriceCreate, AssetPriceUpdate
from app.services.base import BaseService


class AssetPriceService(BaseService):
    """Service responsável por regras de negócio de preços históricos.

    Preços históricos permitem calcular valor de mercado sem depender de uma API
    externa na primeira versão. O service garante que cada preço pertence a um
    ativo do usuário e que não existam dois preços para o mesmo ativo na mesma
    data.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.asset_price_repository = AssetPriceRepository(db=db)
        self.asset_repository = AssetRepository(db=db)

    def create_asset_price(
        self,
        *,
        user_id: UUID,
        data: AssetPriceCreate,
    ) -> AssetPrice:
        """Cria preço histórico para um ativo do usuário."""

        def operation() -> AssetPrice:
            asset = self._get_asset_for_user(user_id=user_id, asset_id=data.asset_id)
            self._ensure_price_currency_matches_asset(
                asset=asset,
                price_currency=data.currency,
            )
            self._ensure_price_date_available(
                user_id=user_id,
                asset_id=data.asset_id,
                price_date=data.price_date,
            )

            asset_price = AssetPrice(
                user_id=user_id,
                asset_id=data.asset_id,
                price_date=data.price_date,
                price=data.price,
                currency=data.currency,
                source=data.source,
            )
            return self.asset_price_repository.create(asset_price)

        return self.run_in_transaction(operation)

    def get_asset_price(
        self,
        *,
        user_id: UUID,
        asset_price_id: UUID,
    ) -> AssetPrice:
        """Busca preço histórico garantindo ownership."""

        asset_price = self.asset_price_repository.get_owned_by_id(
            record_id=asset_price_id,
            user_id=user_id,
        )
        return self.require_found(asset_price, "Preço do ativo")

    def list_asset_prices(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        page: int = 1,
        size: int = 50,
        price_from: date | None = None,
        price_to: date | None = None,
        source: PriceSource | None = None,
        sort_by: str | None = "price_date",
        sort_direction: SortDirection = "desc",
    ) -> tuple[list[AssetPrice], int]:
        """Lista preços históricos de um ativo do usuário."""

        self._get_asset_for_user(user_id=user_id, asset_id=asset_id)

        return self.asset_price_repository.list_by_asset(
            user_id=user_id,
            asset_id=asset_id,
            page=page,
            size=size,
            price_from=price_from,
            price_to=price_to,
            source=source,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def get_latest_asset_price(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
    ) -> AssetPrice | None:
        """Busca o preço mais recente de um ativo do usuário."""

        self._get_asset_for_user(user_id=user_id, asset_id=asset_id)
        return self.asset_price_repository.get_latest_by_asset(
            user_id=user_id,
            asset_id=asset_id,
        )

    def list_latest_asset_prices(self, *, user_id: UUID) -> list[AssetPrice]:
        """Lista os preços mais recentes dos ativos do usuário."""

        return self.asset_price_repository.list_latest_by_user(user_id=user_id)

    def update_asset_price(
        self,
        *,
        user_id: UUID,
        asset_price_id: UUID,
        data: AssetPriceUpdate,
    ) -> AssetPrice:
        """Atualiza preço histórico após validar data e moeda."""

        def operation() -> AssetPrice:
            asset_price = self.get_asset_price(
                user_id=user_id,
                asset_price_id=asset_price_id,
            )
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return asset_price

            asset = self._get_asset_for_user(
                user_id=user_id,
                asset_id=asset_price.asset_id,
            )

            new_currency = update_data.get("currency")
            if new_currency is not None:
                self._ensure_price_currency_matches_asset(
                    asset=asset,
                    price_currency=new_currency,
                )

            new_price_date = update_data.get("price_date")
            if new_price_date is not None and new_price_date != asset_price.price_date:
                self._ensure_price_date_available(
                    user_id=user_id,
                    asset_id=asset_price.asset_id,
                    price_date=new_price_date,
                    current_asset_price_id=asset_price_id,
                )

            return self.asset_price_repository.update(asset_price, update_data)

        return self.run_in_transaction(operation)

    def delete_asset_price(self, *, user_id: UUID, asset_price_id: UUID) -> None:
        """Remove um preço histórico do usuário."""

        def operation() -> None:
            asset_price = self.get_asset_price(
                user_id=user_id,
                asset_price_id=asset_price_id,
            )
            self.asset_price_repository.delete(asset_price)

        self.run_in_transaction(operation)

    def _get_asset_for_user(self, *, user_id: UUID, asset_id: UUID) -> Asset:
        """Busca ativo garantindo ownership antes de manipular preços."""

        asset = self.asset_repository.get_owned_by_id(
            record_id=asset_id,
            user_id=user_id,
        )
        return self.require_found(asset, "Ativo")

    @staticmethod
    def _ensure_price_currency_matches_asset(
        *,
        asset: Asset,
        price_currency: str,
    ) -> None:
        """Garante que o preço usa a mesma moeda do ativo."""

        if asset.currency == price_currency:
            return

        raise ConflictError(
            message="A moeda do preço precisa ser igual à moeda do ativo.",
            details=[
                {
                    "field": "currency",
                    "message": "Informe um preço na mesma moeda cadastrada no ativo.",
                }
            ],
        )

    def _ensure_price_date_available(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        price_date: date,
        current_asset_price_id: UUID | None = None,
    ) -> None:
        """Impede dois preços para o mesmo ativo na mesma data."""

        existing_price = self.asset_price_repository.get_by_asset_and_date(
            user_id=user_id,
            asset_id=asset_id,
            price_date=price_date,
        )

        if existing_price is None:
            return

        if (
            current_asset_price_id is not None
            and existing_price.id == current_asset_price_id
        ):
            return

        raise ConflictError(
            message="Já existe um preço cadastrado para este ativo nesta data.",
            details=[
                {
                    "field": "price_date",
                    "message": "Informe uma data diferente para o preço do ativo.",
                }
            ],
        )
