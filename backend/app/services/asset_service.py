from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.asset import Asset
from app.models.enums import AssetType
from app.repositories import AssetRepository, CategoryRepository, SortDirection
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.base import BaseService


class AssetService(BaseService):
    """Service responsável por regras de negócio de ativos financeiros.

    Ativos pertencem a um usuário e podem estar vinculados a uma categoria. A
    posição do ativo não é persistida aqui porque o projeto usa movimentações
    como fonte da verdade. Por isso, este service valida cadastro, ownership e
    atualização, mas deixa cálculos financeiros para uma etapa específica.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.asset_repository = AssetRepository(db=db)
        self.category_repository = CategoryRepository(db=db)

    def create_asset(self, *, user_id: UUID, data: AssetCreate) -> Asset:
        """Cria um ativo para o usuário atual.

        A categoria é opcional, mas, quando enviada, precisa pertencer ao mesmo
        usuário. Essa validação impede que um usuário vincule seu ativo a uma
        categoria de outra conta apenas conhecendo o UUID.
        """

        def operation() -> Asset:
            if data.category_id is not None:
                self._ensure_category_belongs_to_user(
                    user_id=user_id,
                    category_id=data.category_id,
                )

            self._ensure_symbol_available(user_id=user_id, symbol=data.symbol)

            asset = Asset(
                user_id=user_id,
                category_id=data.category_id,
                symbol=data.symbol,
                name=data.name,
                asset_type=data.asset_type,
                currency=data.currency,
                exchange=data.exchange,
                isin=data.isin,
                is_active=data.is_active,
            )
            return self.asset_repository.create(asset)

        return self.run_in_transaction(operation)

    def get_asset(self, *, user_id: UUID, asset_id: UUID) -> Asset:
        """Busca ativo garantindo que pertence ao usuário informado."""

        asset = self.asset_repository.get_owned_by_id(
            record_id=asset_id,
            user_id=user_id,
        )
        return self.require_found(asset, "Ativo")

    def list_assets(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        asset_type: AssetType | None = None,
        category_id: UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str | None = "symbol",
        sort_direction: SortDirection = "asc",
    ) -> tuple[list[Asset], int]:
        """Lista ativos do usuário com filtros e paginação.

        Quando `category_id` é informado, validamos ownership antes da listagem.
        Isso evita consultas usando categorias de outro usuário como filtro.
        """

        if category_id is not None:
            self._ensure_category_belongs_to_user(
                user_id=user_id,
                category_id=category_id,
            )

        return self.asset_repository.list_by_user(
            user_id=user_id,
            page=page,
            size=size,
            asset_type=asset_type,
            category_id=category_id,
            is_active=is_active,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def list_active_assets(self, *, user_id: UUID) -> list[Asset]:
        """Lista ativos ativos para campos de seleção no frontend."""

        return self.asset_repository.list_active_by_user(user_id=user_id)

    def update_asset(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        data: AssetUpdate,
    ) -> Asset:
        """Atualiza um ativo após validar ownership e duplicidade de símbolo."""

        def operation() -> Asset:
            asset = self.get_asset(user_id=user_id, asset_id=asset_id)
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return asset

            category_id = update_data.get("category_id")
            if category_id is not None:
                self._ensure_category_belongs_to_user(
                    user_id=user_id,
                    category_id=category_id,
                )

            new_symbol = update_data.get("symbol")
            if new_symbol is not None:
                self._ensure_symbol_available(
                    user_id=user_id,
                    symbol=new_symbol,
                    exclude_asset_id=asset_id,
                )

            return self.asset_repository.update(asset, update_data)

        return self.run_in_transaction(operation)

    def deactivate_asset(self, *, user_id: UUID, asset_id: UUID) -> Asset:
        """Desativa um ativo sem apagar seu histórico financeiro.

        Em um organizador financeiro, apagar fisicamente um ativo pode quebrar
        auditoria de movimentações antigas. Por isso, o fluxo padrão é marcar o
        ativo como inativo e escondê-lo das telas principais.
        """

        def operation() -> Asset:
            asset = self.get_asset(user_id=user_id, asset_id=asset_id)
            return self.asset_repository.update(asset, {"is_active": False})

        return self.run_in_transaction(operation)

    def _ensure_category_belongs_to_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        """Garante que a categoria usada no ativo pertence ao usuário."""

        category = self.category_repository.get_owned_by_id(
            record_id=category_id,
            user_id=user_id,
        )
        self.require_found(category, "Categoria")

    def _ensure_symbol_available(
        self,
        *,
        user_id: UUID,
        symbol: str,
        exclude_asset_id: UUID | None = None,
    ) -> None:
        """Garante que o usuário não terá dois ativos com o mesmo símbolo."""

        if not self.asset_repository.symbol_exists(
            user_id=user_id,
            symbol=symbol,
            exclude_asset_id=exclude_asset_id,
        ):
            return

        raise ConflictError(
            message="Já existe um ativo cadastrado com este símbolo.",
            details=[
                {
                    "field": "symbol",
                    "message": "Use um símbolo diferente para o ativo.",
                }
            ],
        )
