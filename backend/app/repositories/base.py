from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

ModelT = TypeVar("ModelT")


class RepositoryConfigurationError(RuntimeError):
    """Erro usado quando um repository é aplicado a um model incompatível.

    Este erro representa falha de configuração do código, não erro causado pelo
    usuário da API. Por isso ele herda de `RuntimeError` e deve aparecer durante
    desenvolvimento/testes, antes de chegar em produção.
    """


class BaseRepository(Generic[ModelT]):
    """Repository base para operações comuns com SQLAlchemy.

    A classe recebe a sessão do banco e o model ORM concreto. Isso permite
    reutilizar operações simples sem acoplar o repository base a um domínio
    específico, mantendo as regras de negócio nos services.
    """

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model

    def get_by_id(self, record_id: UUID) -> ModelT | None:
        """Busca um registro pela chave primária.

        `Session.get` é usado porque é a operação mais direta para buscar por
        primary key e também aproveita o identity map da sessão quando o objeto
        já foi carregado anteriormente.
        """

        return self.db.get(self.model, record_id)

    def list_all(self, *, offset: int = 0, limit: int = 50) -> Sequence[ModelT]:
        """Lista registros sem aplicar filtros de domínio.

        Este método deve ser usado com cuidado em tabelas grandes. Nas rotas
        públicas, o padrão será usar paginação e filtros específicos para evitar
        respostas grandes demais.
        """

        stmt = select(self.model).offset(offset).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def count(self, stmt: Select[Any] | None = None) -> int:
        """Conta registros da tabela ou de uma query específica.

        Quando `stmt` é informado, a query original é transformada em subquery.
        Isso permite contar corretamente listagens que já receberam filtros.
        """

        if stmt is None:
            count_stmt = select(func.count()).select_from(self.model)
        else:
            count_stmt = select(func.count()).select_from(
                stmt.order_by(None).subquery()
            )

        return int(self.db.execute(count_stmt).scalar_one())

    def create(self, instance: ModelT) -> ModelT:
        """Persiste uma instância ORM e retorna o objeto atualizado.

        O `flush` envia a operação para o banco dentro da transação atual sem
        fazer commit. Isso mantém o controle transacional no service ou na rota,
        evitando commits parciais quando uma operação de negócio envolver mais
        de uma escrita.
        """

        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def update(self, instance: ModelT, data: Mapping[str, Any]) -> ModelT:
        """Atualiza atributos simples de uma instância ORM.

        O método recebe um mapping para funcionar bem com dados vindos de schemas
        Pydantic usando `model_dump(exclude_unset=True)` nas próximas etapas.
        """

        for field_name, value in data.items():
            setattr(instance, field_name, value)

        self.db.flush()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """Remove uma instância ORM dentro da transação atual.

        Assim como em `create`, não fazemos commit aqui. A decisão de confirmar
        ou desfazer a transação deve ficar em uma camada superior.
        """

        self.db.delete(instance)
        self.db.flush()

    def get_owned_by_id(self, record_id: UUID, user_id: UUID) -> ModelT | None:
        """Busca um registro por `id` garantindo que pertence ao usuário.

        Este método deve ser usado apenas em models que possuem coluna `user_id`.
        Ele prepara a base para a regra central do projeto: um usuário não pode
        acessar dados financeiros de outro usuário.
        """

        id_column = self._get_required_column("id")
        user_id_column = self._get_required_column("user_id")

        stmt = select(self.model).where(
            id_column == record_id,
            user_id_column == user_id,
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def _get_required_column(self, column_name: str) -> Any:
        """Retorna uma coluna do model ou falha com erro explícito.

        Usar uma mensagem clara reduz tempo de debug quando um repository
        genérico é usado acidentalmente com um model que não possui determinada
        coluna.
        """

        column = getattr(self.model, column_name, None)

        if column is None:
            model_name = getattr(self.model, "__name__", str(self.model))
            raise RepositoryConfigurationError(
                f"Model {model_name} does not define required column '{column_name}'."
            )

        return column
