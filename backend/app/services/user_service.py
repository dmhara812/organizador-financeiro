from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, AuthorizationError
from app.models.user import User
from app.repositories import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import BaseService


class UserService(BaseService):
    """Service responsável por regras de negócio de usuários.

    A autenticação JWT ainda será implementada na Etapa 6. Mesmo assim, este
    service já centraliza criação, atualização e desativação de usuários para
    que a etapa de autenticação não precise acessar repositories diretamente.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.user_repository = UserRepository(db=db)

    def get_user(self, user_id: UUID) -> User:
        """Busca um usuário pelo ID ou lança erro padronizado.

        Este método será útil para rotas autenticadas que precisem carregar o
        usuário atual depois que o JWT for validado.
        """

        user = self.user_repository.get_by_id(user_id)
        return self.require_found(user, "Usuário")

    def get_active_user(self, user_id: UUID) -> User:
        """Busca usuário ativo e bloqueia contas desativadas.

        Separar esta regra evita repetir `is_active` em cada rota futura. Usuário
        inativo existe no banco, mas não deve conseguir usar a aplicação.
        """

        user = self.get_user(user_id)
        if not user.is_active:
            raise AuthorizationError(message="Usuário inativo.")

        return user

    def get_by_email(self, email: str) -> User | None:
        """Busca usuário por e-mail normalizado.

        Retornar `None` aqui é intencional porque a autenticação da Etapa 6
        precisará diferenciar busca vazia de usuário encontrado com senha errada.
        """

        return self.user_repository.get_by_email(email)

    def create_user(self, data: UserCreate, *, hashed_password: str) -> User:
        """Cria um usuário usando senha já convertida em hash.

        O service não recebe nem persiste senha pura. A Etapa 6 criará o hash
        antes de chamar este método. Essa assinatura reduz o risco de salvar uma
        senha em texto puro por engano.
        """

        def operation() -> User:
            self.ensure_valid(
                bool(hashed_password.strip()),
                "A senha criptografada é obrigatória para criar um usuário.",
                field="hashed_password",
            )

            if self.user_repository.email_exists(str(data.email)):
                raise ConflictError(
                    message="Já existe um usuário cadastrado com este e-mail.",
                    details=[
                        {
                            "field": "email",
                            "message": "Informe outro e-mail para continuar.",
                        }
                    ],
                )

            user = User(
                email=str(data.email),
                hashed_password=hashed_password,
                full_name=data.full_name,
                is_active=True,
            )
            return self.user_repository.create(user)

        return self.run_in_transaction(operation)

    def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        """Atualiza dados básicos do usuário.

        Atualização de senha ficará em fluxo próprio na etapa de autenticação,
        porque exige validações diferentes, como senha atual e novo hash.
        """

        def operation() -> User:
            user = self.get_user(user_id)
            update_data = data.model_dump(exclude_unset=True)

            if not update_data:
                return user

            return self.user_repository.update(user, update_data)

        return self.run_in_transaction(operation)

    def deactivate_user(self, user_id: UUID) -> User:
        """Desativa um usuário sem apagar seus dados financeiros.

        Delete físico apagaria categorias, corretoras, ativos e movimentações em
        cascata. Para um organizador financeiro, preservar histórico é mais
        seguro e facilita auditoria futura.
        """

        def operation() -> User:
            user = self.get_user(user_id)
            return self.user_repository.update(user, {"is_active": False})

        return self.run_in_transaction(operation)
