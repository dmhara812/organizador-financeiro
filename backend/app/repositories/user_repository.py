from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository específico para consultas de usuários.

    Usuários serão usados na autenticação da Etapa 6. Por isso, este repository
    já centraliza consultas por e-mail e por status ativo, evitando repetir
    filtros sensíveis em services diferentes.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db, model=User)

    def get_by_email(self, email: str) -> User | None:
        """Busca um usuário pelo e-mail de forma case-insensitive.

        O login não deve depender da forma como o usuário digitou letras
        maiúsculas ou minúsculas. Normalizar aqui também protege chamadas
        internas feitas por services futuros.
        """

        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return None

        stmt = select(User).where(func.lower(User.email) == normalized_email)
        return self.db.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str, *, exclude_user_id: UUID | None = None) -> bool:
        """Verifica se um e-mail já está em uso.

        `exclude_user_id` permite reutilizar a mesma regra em atualização de
        perfil, onde o usuário atual pode manter o próprio e-mail sem gerar falso
        positivo de duplicidade.
        """

        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return False

        stmt = select(User.id).where(func.lower(User.email) == normalized_email)

        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)

        return self.db.execute(stmt).first() is not None

    def list_active(self, *, offset: int = 0, limit: int = 50) -> Sequence[User]:
        """Lista usuários ativos.

        Este método não será exposto diretamente para usuários comuns. Ele deixa
        preparada uma consulta útil para tarefas administrativas ou testes
        futuros sem espalhar o filtro `is_active` pelo projeto.
        """

        stmt = select(User).where(User.is_active.is_(True)).offset(offset).limit(limit)
        return self.db.execute(stmt).scalars().all()

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Normaliza e-mail para consultas consistentes."""

        return email.strip().lower()
