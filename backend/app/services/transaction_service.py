from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.repositories import (
    AssetRepository,
    BrokerageRepository,
    SortDirection,
    TransactionRepository,
)
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.base import BaseService


class TransactionService(BaseService):
    """Service responsável por regras de negócio de movimentações.

    Movimentações são a fonte da verdade do produto. Este service garante que
    vínculos opcionais, como ativo e corretora, pertencem ao usuário antes de
    salvar a movimentação. Cálculos de posição e patrimônio serão adicionados em
    services de relatório para manter esta etapa pequena e validável.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.transaction_repository = TransactionRepository(db=db)
        self.asset_repository = AssetRepository(db=db)
        self.brokerage_repository = BrokerageRepository(db=db)

    def create_transaction(
        self,
        *,
        user_id: UUID,
        data: TransactionCreate,
    ) -> Transaction:
        """Cria movimentação financeira para o usuário atual."""

        def operation() -> Transaction:
            self._ensure_related_records_belong_to_user(
                user_id=user_id,
                asset_id=data.asset_id,
                brokerage_id=data.brokerage_id,
            )
            self._ensure_external_reference_available(
                user_id=user_id,
                external_reference=data.external_reference,
            )

            transaction = Transaction(
                user_id=user_id,
                asset_id=data.asset_id,
                brokerage_id=data.brokerage_id,
                transaction_type=data.transaction_type,
                occurred_at=data.occurred_at,
                quantity=data.quantity,
                unit_price=data.unit_price,
                gross_amount=data.gross_amount,
                fee_amount=data.fee_amount,
                tax_amount=data.tax_amount,
                net_amount=data.net_amount,
                currency=data.currency,
                notes=data.notes,
                external_reference=data.external_reference,
            )
            return self.transaction_repository.create(transaction)

        return self.run_in_transaction(operation)

    def get_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
    ) -> Transaction:
        """Busca movimentação garantindo ownership."""

        transaction = self.transaction_repository.get_owned_by_id(
            record_id=transaction_id,
            user_id=user_id,
        )
        return self.require_found(transaction, "Movimentação")

    def list_transactions(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        asset_id: UUID | None = None,
        brokerage_id: UUID | None = None,
        transaction_type: TransactionType | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        sort_by: str | None = "occurred_at",
        sort_direction: SortDirection = "desc",
    ) -> tuple[list[Transaction], int]:
        """Lista movimentações do usuário com filtros de domínio."""

        self._ensure_related_records_belong_to_user(
            user_id=user_id,
            asset_id=asset_id,
            brokerage_id=brokerage_id,
        )

        return self.transaction_repository.list_by_user(
            user_id=user_id,
            page=page,
            size=size,
            asset_id=asset_id,
            brokerage_id=brokerage_id,
            transaction_type=transaction_type,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def list_recent_transactions(
        self,
        *,
        user_id: UUID,
        limit: int = 10,
    ) -> list[Transaction]:
        """Lista movimentações recentes para dashboard ou resumo inicial."""

        return self.transaction_repository.list_recent_by_user(
            user_id=user_id,
            limit=limit,
        )

    def update_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        data: TransactionUpdate,
    ) -> Transaction:
        """Atualiza movimentação após validar ownership dos relacionamentos."""

        def operation() -> Transaction:
            transaction = self.get_transaction(
                user_id=user_id,
                transaction_id=transaction_id,
            )
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return transaction

            self._ensure_related_records_belong_to_user(
                user_id=user_id,
                asset_id=update_data.get("asset_id"),
                brokerage_id=update_data.get("brokerage_id"),
            )
            self._ensure_external_reference_available(
                user_id=user_id,
                external_reference=update_data.get("external_reference"),
                current_transaction_id=transaction_id,
            )

            return self.transaction_repository.update(transaction, update_data)

        return self.run_in_transaction(operation)

    def delete_transaction(self, *, user_id: UUID, transaction_id: UUID) -> None:
        """Remove movimentação do usuário.

        Como as movimentações são a fonte da verdade, essa operação deve ser
        usada com cuidado nas rotas futuras. Por enquanto, ela existe para dar
        suporte à tela de gestão, mas o histórico de auditoria avançado pode ser
        implementado depois com soft delete ou eventos.
        """

        def operation() -> None:
            transaction = self.get_transaction(
                user_id=user_id,
                transaction_id=transaction_id,
            )
            self.transaction_repository.delete(transaction)

        self.run_in_transaction(operation)

    def _ensure_related_records_belong_to_user(
        self,
        *,
        user_id: UUID,
        asset_id: UUID | None = None,
        brokerage_id: UUID | None = None,
    ) -> None:
        """Valida ownership de ativo e corretora antes de salvar vínculos."""

        if asset_id is not None:
            asset = self.asset_repository.get_owned_by_id(
                record_id=asset_id,
                user_id=user_id,
            )
            self.require_found(asset, "Ativo")

        if brokerage_id is not None:
            brokerage = self.brokerage_repository.get_owned_by_id(
                record_id=brokerage_id,
                user_id=user_id,
            )
            self.require_found(brokerage, "Corretora")

    def _ensure_external_reference_available(
        self,
        *,
        user_id: UUID,
        external_reference: str | None,
        current_transaction_id: UUID | None = None,
    ) -> None:
        """Impede duplicidade de referência externa por usuário.

        Essa regra prepara a futura importação CSV, em que uma linha importada
        pode trazer um identificador externo para evitar importações duplicadas.
        """

        if external_reference is None:
            return

        existing_transaction = self.transaction_repository.get_by_external_reference(
            user_id=user_id,
            external_reference=external_reference,
        )

        if existing_transaction is None:
            return

        if (
            current_transaction_id is not None
            and existing_transaction.id == current_transaction_id
        ):
            return

        raise ConflictError(
            message="Já existe uma movimentação com esta referência externa.",
            details=[
                {
                    "field": "external_reference",
                    "message": "Use uma referência externa diferente.",
                }
            ],
        )
