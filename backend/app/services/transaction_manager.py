from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn, TypeVar

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AppException,
    ConflictError,
    DatabaseUnavailableError,
)

ResultT = TypeVar("ResultT")


class TransactionManager:
    """Centraliza o controle transacional usado pelos services.

    Os repositories executam operações de banco e podem usar `flush`, mas não
    fazem `commit`. O service decide quando uma regra de negócio terminou com
    sucesso. Esta classe mantém esse controle em um único lugar para evitar
    repetição e commits parciais.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        """Confirma a transação atual.

        Erros técnicos do SQLAlchemy são convertidos para exceções da aplicação.
        Assim, os handlers globais conseguem transformar o erro em uma resposta
        HTTP padronizada sem que a camada de service dependa diretamente do
        FastAPI.
        """

        try:
            self.db.commit()
        except IntegrityError as exc:
            self._raise_conflict_error(exc)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def rollback(self) -> None:
        """Desfaz a transação atual.

        Este método é exposto para os services que precisarem cancelar uma
        operação manualmente. Na maior parte dos casos, `run` será suficiente.
        """

        self.db.rollback()

    def run(self, operation: Callable[[], ResultT]) -> ResultT:
        """Executa uma operação dentro de uma transação.

        A função recebida deve conter a regra de negócio. Se ela terminar sem
        exceções, fazemos `commit`. Se lançar erro de negócio ou erro de banco,
        fazemos `rollback` e propagamos uma exceção padronizada.
        """

        try:
            result = operation()
        except AppException:
            self._rollback_safely()
            raise
        except IntegrityError as exc:
            self._raise_conflict_error(exc)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        self.commit()
        return result

    def _raise_conflict_error(self, exc: IntegrityError) -> NoReturn:
        """Converte conflitos de integridade do banco para erro de aplicação.

        `IntegrityError` costuma indicar violação de constraint, como registros
        duplicados em campos únicos. A mensagem retornada é propositalmente
        genérica para não vazar nomes internos de constraints ou tabelas.
        """

        self._rollback_safely()
        raise ConflictError(
            message="A operação não pôde ser concluída por conflito com dados existentes.",
            details=[
                {
                    "field": "database",
                    "message": "Verifique se o registro já existe ou viola uma regra de unicidade.",
                }
            ],
        ) from exc

    def _raise_database_error(self, exc: SQLAlchemyError) -> NoReturn:
        """Converte erros gerais do SQLAlchemy para erro padronizado da API."""

        self._rollback_safely()
        raise DatabaseUnavailableError() from exc

    def _rollback_safely(self) -> None:
        """Executa rollback sem esconder o erro original.

        Se o rollback também falhar, mantemos a exceção original como a causa
        principal. Isso evita trocar um erro de negócio ou de banco por uma falha
        secundária de limpeza da sessão.
        """

        try:
            self.db.rollback()
        except SQLAlchemyError:
            pass
