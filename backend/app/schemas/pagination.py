from typing import Generic, TypeVar

from pydantic import Field, computed_field

from app.schemas.base import AppBaseModel

SchemaT = TypeVar("SchemaT")


class PaginationParams(AppBaseModel):
    """Parâmetros padronizados para listagens paginadas.

    `page` começa em 1 porque esse padrão é mais amigável para o frontend e
    para usuários. O `offset` é derivado para uso interno nos repositories.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """Calcula o deslocamento usado em queries SQL com limit/offset."""

        return (self.page - 1) * self.page_size


class PaginatedResponse(AppBaseModel, Generic[SchemaT]):
    """Resposta genérica para endpoints de listagem.

    O backend sempre retorna `items` e metadados de paginação no mesmo formato.
    Isso reduz condicionais no frontend e facilita criar componentes de tabela
    reutilizáveis nas etapas de telas de gestão.
    """

    items: list[SchemaT]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calcula o total de páginas sem depender do frontend."""

        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        """Indica se existe próxima página disponível."""

        return self.page < self.total_pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        """Indica se existe página anterior disponível."""

        return self.page > 1
