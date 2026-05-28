from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

ModelT = TypeVar("ModelT")

SortDirection = Literal["asc", "desc"]


def calculate_offset(page: int, size: int) -> int:
    """Calcula o offset de uma listagem paginada.

    A API trabalha com páginas iniciando em 1 porque esse formato é mais natural
    para o frontend e para o usuário final. O banco, por outro lado, trabalha
    com deslocamento iniciando em 0.
    """

    if page < 1:
        raise ValueError("Page must be greater than or equal to 1.")

    if size < 1:
        raise ValueError("Size must be greater than or equal to 1.")

    return (page - 1) * size


def calculate_total_pages(total: int, size: int) -> int:
    """Calcula o total de páginas a partir do total de registros.

    Quando não há registros, retornamos 0 páginas. Isso deixa explícito para o
    frontend que a lista está vazia, em vez de sugerir que existe uma página 1
    com conteúdo.
    """

    if total < 0:
        raise ValueError("Total must be greater than or equal to 0.")

    if size < 1:
        raise ValueError("Size must be greater than or equal to 1.")

    if total == 0:
        return 0

    return (total + size - 1) // size


def apply_pagination(stmt: Select[Any], *, page: int, size: int) -> Select[Any]:
    """Aplica `offset` e `limit` em uma query SQLAlchemy.

    A função recebe a query já montada para que repositories específicos possam
    aplicar filtros antes da paginação.
    """

    offset = calculate_offset(page=page, size=size)
    return stmt.offset(offset).limit(size)


def count_select(db: Session, stmt: Select[Any]) -> int:
    """Conta os registros retornados por uma query.

    Removemos `order_by` antes de contar porque ordenação não altera o total e
    pode deixar a consulta de contagem mais custosa em algumas situações.
    """

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(db.execute(count_stmt).scalar_one())


def paginate_select(
    db: Session,
    stmt: Select[Any],
    *,
    page: int,
    size: int,
) -> tuple[list[ModelT], int]:
    """Executa uma query paginada e retorna itens e total.

    O retorno separado, `(items, total)`, dá flexibilidade para os services
    montarem a resposta final usando os schemas adequados de cada domínio.
    """

    total = count_select(db=db, stmt=stmt)
    paginated_stmt = apply_pagination(stmt, page=page, size=size)
    items = list(db.execute(paginated_stmt).scalars().all())

    return items, total


def apply_order_by(
    stmt: Select[Any],
    *,
    model: type[Any],
    sort_by: str | None,
    sort_direction: SortDirection = "asc",
    allowed_fields: Iterable[str] | None = None,
) -> Select[Any]:
    """Aplica ordenação segura em uma query.

    A lista `allowed_fields` impede que a API aceite qualquer string vinda do
    frontend e tente transformá-la em coluna. Isso reduz risco de bugs e mantém
    contratos de listagem previsíveis.
    """

    if sort_by is None:
        return stmt

    allowed_fields_set = set(allowed_fields or [])

    if allowed_fields_set and sort_by not in allowed_fields_set:
        raise ValueError(f"Sorting by '{sort_by}' is not allowed.")

    column = getattr(model, sort_by, None)

    if column is None:
        model_name = getattr(model, "__name__", str(model))
        raise ValueError(f"Model {model_name} does not define column '{sort_by}'.")

    if sort_direction == "desc":
        return stmt.order_by(desc(column))

    return stmt.order_by(asc(column))
