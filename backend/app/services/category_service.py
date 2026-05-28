from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.category import Category
from app.repositories import CategoryRepository, SortDirection
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.base import BaseService


class CategoryService(BaseService):
    """Service responsável por regras de negócio de categorias.

    Categorias pertencem a um usuário e serão usadas para classificar ativos e
    alimentar gráficos futuros. Por isso, todos os métodos recebem `user_id` e
    validam ownership antes de alterar ou retornar dados sensíveis.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.category_repository = CategoryRepository(db=db)

    def create_category(self, *, user_id: UUID, data: CategoryCreate) -> Category:
        """Cria categoria para um usuário.

        A regra de unicidade por usuário é validada aqui para devolver erro de
        negócio amigável antes de depender apenas da constraint do banco.
        """

        def operation() -> Category:
            self._ensure_name_available(user_id=user_id, name=data.name)

            category = Category(
                user_id=user_id,
                name=data.name,
                description=data.description,
                color=data.color,
            )
            return self.category_repository.create(category)

        return self.run_in_transaction(operation)

    def get_category(self, *, user_id: UUID, category_id: UUID) -> Category:
        """Busca categoria garantindo que ela pertence ao usuário.

        Esse padrão será reaproveitado pelas rotas protegidas para impedir que
        um usuário acesse categorias de outra conta apenas alterando o UUID.
        """

        category = self.category_repository.get_owned_by_id(
            record_id=category_id,
            user_id=user_id,
        )
        return self.require_found(category, "Categoria")

    def list_categories(
        self,
        *,
        user_id: UUID,
        page: int = 1,
        size: int = 50,
        search: str | None = None,
        sort_by: str | None = "name",
        sort_direction: SortDirection = "asc",
    ) -> tuple[list[Category], int]:
        """Lista categorias do usuário com paginação e busca opcional.

        O retorno `(items, total)` será convertido em `PaginatedResponse` pela
        rota futura, mantendo o service independente da camada HTTP.
        """

        return self.category_repository.list_by_user(
            user_id=user_id,
            page=page,
            size=size,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def update_category(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
        data: CategoryUpdate,
    ) -> Category:
        """Atualiza categoria após validar ownership e duplicidade de nome."""

        def operation() -> Category:
            category = self.get_category(user_id=user_id, category_id=category_id)
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return category

            new_name = update_data.get("name")
            if new_name is not None:
                self._ensure_name_available(
                    user_id=user_id,
                    name=new_name,
                    exclude_category_id=category_id,
                )

            return self.category_repository.update(category, update_data)

        return self.run_in_transaction(operation)

    def delete_category(self, *, user_id: UUID, category_id: UUID) -> None:
        """Remove categoria do usuário.

        A migration inicial definiu `SET NULL` para ativos associados à
        categoria. Assim, remover uma categoria não apaga os ativos; eles apenas
        deixam de ter essa classificação.
        """

        def operation() -> None:
            category = self.get_category(user_id=user_id, category_id=category_id)
            self.category_repository.delete(category)

        self.run_in_transaction(operation)

    def _ensure_name_available(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_category_id: UUID | None = None,
    ) -> None:
        """Garante que o usuário não terá duas categorias com mesmo nome."""

        if not self.category_repository.name_exists(
            user_id=user_id,
            name=name,
            exclude_category_id=exclude_category_id,
        ):
            return

        raise ConflictError(
            message="Já existe uma categoria com este nome.",
            details=[
                {
                    "field": "name",
                    "message": "Use um nome diferente para a categoria.",
                }
            ],
        )
