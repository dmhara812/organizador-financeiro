from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError, ValidationAppError
from app.services.transaction_manager import TransactionManager

EntityT = TypeVar("EntityT")
ResultT = TypeVar("ResultT")


class BaseService:
    """Classe base para services de domínio.

    Services são responsáveis por regras de negócio e coordenação de
    repositories. A classe base oferece utilitários comuns, mas não conhece
    detalhes de usuários, ativos, corretoras, categorias ou movimentações.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.transaction = TransactionManager(db=db)

    def commit(self) -> None:
        """Confirma a transação atual usando tratamento padronizado.

        Este método existe para casos em que o service precisa controlar o fluxo
        manualmente. Em casos simples, prefira `run_in_transaction`.
        """

        self.transaction.commit()

    def rollback(self) -> None:
        """Desfaz a transação atual.

        Manter este método no service evita que services concretos manipulem a
        sessão diretamente quando precisarem cancelar uma operação.
        """

        self.transaction.rollback()

    def run_in_transaction(self, operation: Callable[[], ResultT]) -> ResultT:
        """Executa uma regra de negócio dentro de uma transação.

        A função `operation` deve chamar repositories e aplicar validações. Se
        tudo der certo, a transação é confirmada. Se algo falhar, o rollback é
        executado pelo `TransactionManager`.
        """

        return self.transaction.run(operation)

    @staticmethod
    def require_found(entity: EntityT | None, resource_name: str) -> EntityT:
        """Garante que um recurso foi encontrado.

        Repositories retornam `None` quando não encontram registros. Services
        usam este helper para transformar esse resultado em erro de domínio
        padronizado, que depois será convertido em HTTP 404 pelos handlers.
        """

        if entity is None:
            raise ResourceNotFoundError(resource_name=resource_name)

        return entity

    @staticmethod
    def ensure_valid(
        condition: bool,
        message: str,
        *,
        field: str = "business_rule",
    ) -> None:
        """Valida uma regra de negócio genérica.

        Este helper será útil em services futuros, por exemplo para impedir venda
        de quantidade maior do que a posição disponível. A resposta mantém o
        mesmo formato de erro definido na Etapa 4.3.
        """

        if condition:
            return

        raise ValidationAppError(
            message=message,
            details=[
                {
                    "field": field,
                    "message": message,
                }
            ],
        )
