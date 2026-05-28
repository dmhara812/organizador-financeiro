from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.brokerage import Brokerage
from app.repositories import BrokerageRepository, SortDirection
from app.schemas.brokerage import BrokerageCreate, BrokerageUpdate
from app.services.base import BaseService


class BrokerageService(BaseService):
    """Service responsável por regras de negócio de corretoras.

    Corretoras pertencem ao usuário e serão usadas para filtros, relatórios e
    gestão de movimentações. Por isso, todos os métodos de leitura e escrita
    recebem `user_id` para preservar ownership.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.brokerage_repository = BrokerageRepository(db=db)

    def create_brokerage(self, *, user_id: UUID, data: BrokerageCreate) -> Brokerage:
        """Cria uma corretora para o usuário atual."""

        def operation() -> Brokerage:
            self._ensure_name_available(user_id=user_id, name=data.name)

            brokerage = Brokerage(
                user_id=user_id,
                name=data.name,
                country=data.country,
                website=data.website,
            )
            return self.brokerage_repository.create(brokerage)

        return self.run_in_transaction(operation)

    def get_brokerage(self, *, user_id: UUID, brokerage_id: UUID) -> Brokerage:
        """Busca corretora garantindo ownership.

        Essa validação será essencial nas rotas protegidas, porque o frontend não
        deve conseguir acessar corretoras de outro usuário apenas conhecendo um
        UUID válido.
        """

        brokerage = self.brokerage_repository.get_owned_by_id(
            record_id=brokerage_id,
            user_id=user_id,
        )
        return self.require_found(brokerage, "Corretora")

    def list_brokerages(
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
        """Lista corretoras do usuário com filtros opcionais.

        O filtro por país prepara o backend para telas de gestão e relatórios por
        instituição, sem misturar dados de usuários diferentes.
        """

        return self.brokerage_repository.list_by_user(
            user_id=user_id,
            page=page,
            size=size,
            search=search,
            country=country,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def update_brokerage(
        self,
        *,
        user_id: UUID,
        brokerage_id: UUID,
        data: BrokerageUpdate,
    ) -> Brokerage:
        """Atualiza corretora após validar ownership e duplicidade de nome."""

        def operation() -> Brokerage:
            brokerage = self.get_brokerage(
                user_id=user_id,
                brokerage_id=brokerage_id,
            )
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return brokerage

            new_name = update_data.get("name")
            if new_name is not None:
                self._ensure_name_available(
                    user_id=user_id,
                    name=new_name,
                    exclude_brokerage_id=brokerage_id,
                )

            return self.brokerage_repository.update(brokerage, update_data)

        return self.run_in_transaction(operation)

    def delete_brokerage(self, *, user_id: UUID, brokerage_id: UUID) -> None:
        """Remove corretora do usuário.

        A migration inicial definiu `SET NULL` para movimentações associadas à
        corretora. Assim, remover uma corretora não apaga o histórico financeiro;
        as movimentações apenas deixam de apontar para essa instituição.
        """

        def operation() -> None:
            brokerage = self.get_brokerage(
                user_id=user_id,
                brokerage_id=brokerage_id,
            )
            self.brokerage_repository.delete(brokerage)

        self.run_in_transaction(operation)

    def _ensure_name_available(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_brokerage_id: UUID | None = None,
    ) -> None:
        """Garante que o usuário não terá duas corretoras com mesmo nome."""

        if not self.brokerage_repository.name_exists(
            user_id=user_id,
            name=name,
            exclude_brokerage_id=exclude_brokerage_id,
        ):
            return

        raise ConflictError(
            message="Já existe uma corretora com este nome.",
            details=[
                {
                    "field": "name",
                    "message": "Use um nome diferente para a corretora.",
                }
            ],
        )
