from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationAppError
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
from app.services.portfolio_service import PortfolioService

ZERO = Decimal("0")
POSITION_DECREASE_TYPES = {
    TransactionType.SELL,
    TransactionType.TRANSFER_OUT,
}
POSITION_VALIDATION_UPDATE_FIELDS = {
    "transaction_type",
    "asset_id",
    "quantity",
    "occurred_at",
}


@dataclass(frozen=True, slots=True)
class PositionValidationData:
    """Dados mínimos para validar se uma movimentação pode reduzir posição.

    Usamos uma dataclass pequena para evitar espalhar dicionários com chaves
    soltas pelo service. Isso deixa mais claro quais campos realmente importam
    para a regra de venda/saída.
    """

    transaction_type: TransactionType
    asset_id: UUID | None
    quantity: Decimal | None
    occurred_at: datetime


class TransactionService(BaseService):
    """Service responsável por regras de negócio de movimentações.

    Movimentações são a fonte da verdade do produto. Este service garante que
    vínculos opcionais, como ativo e corretora, pertencem ao usuário antes de
    salvar a movimentação. Também impede que vendas e transferências de saída
    deixem a posição do usuário negativa.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.transaction_repository = TransactionRepository(db=db)
        self.asset_repository = AssetRepository(db=db)
        self.brokerage_repository = BrokerageRepository(db=db)
        self.portfolio_service = PortfolioService(db=db)

    def create_transaction(
        self,
        *,
        user_id: UUID,
        data: TransactionCreate,
    ) -> Transaction:
        """Cria movimentação financeira para o usuário atual.

        Antes de salvar, validamos ownership e posição disponível. Isso evita
        que o banco aceite uma venda maior do que a quantidade existente no
        ativo, preservando a consistência da carteira.
        """

        def operation() -> Transaction:
            self._ensure_related_records_belong_to_user(
                user_id=user_id,
                asset_id=data.asset_id,
                brokerage_id=data.brokerage_id,
            )
            self._ensure_position_available(
                user_id=user_id,
                data=PositionValidationData(
                    transaction_type=data.transaction_type,
                    asset_id=data.asset_id,
                    quantity=data.quantity,
                    occurred_at=data.occurred_at,
                ),
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
        """Atualiza movimentação após validar ownership e posição disponível."""

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

            if self._should_validate_position_on_update(update_data):
                self._ensure_position_available(
                    user_id=user_id,
                    data=self._build_position_validation_data(
                        transaction=transaction,
                        update_data=update_data,
                    ),
                    exclude_transaction_id=transaction_id,
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

    def _ensure_position_available(
        self,
        *,
        user_id: UUID,
        data: PositionValidationData,
        exclude_transaction_id: UUID | None = None,
    ) -> None:
        """Impede vendas ou transferências de saída acima da posição disponível."""

        if data.transaction_type not in POSITION_DECREASE_TYPES:
            return

        if data.asset_id is None:
            raise ValidationAppError(
                message="Movimentações de saída exigem um ativo.",
                details=[
                    {
                        "field": "asset_id",
                        "message": "Informe o ativo que terá posição reduzida.",
                    }
                ],
            )

        if data.quantity is None or data.quantity <= ZERO:
            raise ValidationAppError(
                message="Movimentações de saída exigem quantidade positiva.",
                details=[
                    {
                        "field": "quantity",
                        "message": "Informe uma quantidade maior que zero.",
                    }
                ],
            )

        available_quantity = self.portfolio_service.calculate_available_quantity(
            user_id=user_id,
            asset_id=data.asset_id,
            occurred_to=data.occurred_at,
            exclude_transaction_id=exclude_transaction_id,
        )

        if data.quantity <= available_quantity:
            return

        raise ValidationAppError(
            message="Quantidade insuficiente para concluir a movimentação.",
            details=[
                {
                    "field": "quantity",
                    "message": "A quantidade informada é maior que a posição disponível.",
                    "available_quantity": str(available_quantity),
                    "requested_quantity": str(data.quantity),
                }
            ],
        )

    @staticmethod
    def _should_validate_position_on_update(update_data: dict[str, object]) -> bool:
        """Verifica se o update alterou algum campo que afeta posição.

        Alterações em observações, taxas, impostos ou referência externa não
        mudam quantidade disponível. Evitar validação nesses casos permite
        corrigir metadados sem recalcular a posição desnecessariamente.
        """

        return bool(POSITION_VALIDATION_UPDATE_FIELDS.intersection(update_data))

    @staticmethod
    def _build_position_validation_data(
        *,
        transaction: Transaction,
        update_data: dict[str, object],
    ) -> PositionValidationData:
        """Monta os dados efetivos da movimentação depois do update parcial."""

        transaction_type = update_data.get(
            "transaction_type",
            transaction.transaction_type,
        )
        asset_id = (
            update_data["asset_id"]
            if "asset_id" in update_data
            else transaction.asset_id
        )
        quantity = (
            update_data["quantity"]
            if "quantity" in update_data
            else transaction.quantity
        )
        occurred_at = update_data.get("occurred_at", transaction.occurred_at)

        return PositionValidationData(
            transaction_type=transaction_type,
            asset_id=asset_id,
            quantity=quantity,
            occurred_at=occurred_at,
        )

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
