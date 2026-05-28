from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository
from app.repositories.query_utils import SortDirection, apply_order_by, paginate_select


class TransactionRepository(BaseRepository[Transaction]):
    """Repository específico para consultas de movimentações financeiras.

    A tabela de movimentações é a fonte da verdade do domínio. Mesmo assim, este
    repository não calcula patrimônio ou rentabilidade; ele apenas fornece dados
    filtrados para que os services apliquem as regras financeiras.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=Transaction)

    def list_by_user(
        self,
        user_id: UUID,
        *,
        page: int,
        size: int,
        asset_id: UUID | None = None,
        brokerage_id: UUID | None = None,
        transaction_type: TransactionType | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        sort_by: str | None = "occurred_at",
        sort_direction: SortDirection = "desc",
    ) -> tuple[list[Transaction], int]:
        """Lista movimentações do usuário com filtros e paginação.

        Os filtros refletem necessidades do escopo mínimo: período, corretora,
        tipo de movimentação e ativo. Eles serão expostos nas rotas futuras.
        """

        stmt = select(Transaction).where(Transaction.user_id == user_id)

        if asset_id is not None:
            stmt = stmt.where(Transaction.asset_id == asset_id)

        if brokerage_id is not None:
            stmt = stmt.where(Transaction.brokerage_id == brokerage_id)

        if transaction_type is not None:
            stmt = stmt.where(Transaction.transaction_type == transaction_type)

        if occurred_from is not None:
            stmt = stmt.where(Transaction.occurred_at >= occurred_from)

        if occurred_to is not None:
            stmt = stmt.where(Transaction.occurred_at <= occurred_to)

        stmt = apply_order_by(
            stmt,
            model=Transaction,
            sort_by=sort_by,
            sort_direction=sort_direction,
            allowed_fields={
                "occurred_at",
                "transaction_type",
                "gross_amount",
                "net_amount",
                "created_at",
                "updated_at",
            },
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    def list_by_asset(
        self,
        user_id: UUID,
        asset_id: UUID,
        *,
        page: int,
        size: int,
    ) -> tuple[list[Transaction], int]:
        """Lista movimentações de um ativo pertencente ao usuário."""

        stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.asset_id == asset_id,
            )
            .order_by(Transaction.occurred_at.desc())
        )

        return paginate_select(self.db, stmt, page=page, size=size)

    def list_recent_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 10,
    ) -> list[Transaction]:
        """Lista movimentações recentes para uso em dashboard ou resumo.

        O limite é recebido como argumento para permitir que o service controle
        quanto será exibido sem duplicar a query.
        """

        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.occurred_at.desc())
            .limit(limit)
        )

        return list(self.db.execute(stmt).scalars().all())

    def get_by_external_reference(
        self,
        user_id: UUID,
        external_reference: str,
    ) -> Transaction | None:
        """Busca movimentação por referência externa.

        Este método prepara a futura importação por CSV, onde uma linha pode ter
        identificador externo para evitar importações duplicadas.
        """

        normalized_reference = external_reference.strip()
        if not normalized_reference:
            return None

        stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.external_reference == normalized_reference,
        )

        return self.db.execute(stmt).scalar_one_or_none()
