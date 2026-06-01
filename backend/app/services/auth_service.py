from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterResponse, TokenResponse
from app.schemas.user import UserCreate
from app.services.base import BaseService
from app.services.user_service import UserService


class AuthService(BaseService):
    """Service responsável pelos fluxos de autenticação.

    Este service orquestra regras que envolvem senha, usuário ativo e emissão de
    token. Ele não cria rotas HTTP diretamente; as rotas futuras chamarão estes
    métodos para manter controllers pequenos e fáceis de testar.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.user_service = UserService(db=db)

    def register(self, data: UserCreate) -> RegisterResponse:
        """Registra um usuário e devolve token de acesso.

        A senha pura só existe dentro deste fluxo por tempo suficiente para
        gerar o hash. O `UserService` recebe apenas `hashed_password`, reduzindo
        o risco de persistir senha em texto puro por engano.
        """

        hashed_password = hash_password(data.password)
        user = self.user_service.create_user(data, hashed_password=hashed_password)
        token = self.create_token_for_user(user)

        return RegisterResponse(user=user, token=token)

    def login(self, data: LoginRequest) -> TokenResponse:
        """Autentica usuário e devolve token de acesso.

        A validação de credenciais fica separada de `create_token_for_user` para
        permitir reuso futuro em testes, refresh token ou auditoria de login.
        """

        user = self.authenticate_user(email=str(data.email), password=data.password)
        return self.create_token_for_user(user)

    def authenticate_user(self, *, email: str, password: str) -> User:
        """Valida e-mail, senha e status ativo do usuário.

        O erro de e-mail inexistente e senha incorreta é propositalmente o mesmo
        para não permitir que alguém descubra quais e-mails estão cadastrados.
        """

        user = self.user_service.get_by_email(email.strip().lower())

        if user is None:
            raise AuthenticationError(message="E-mail ou senha inválidos.")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError(message="E-mail ou senha inválidos.")

        if not user.is_active:
            raise ForbiddenError(message="Usuário inativo.")

        return user

    def create_token_for_user(self, user: User) -> TokenResponse:
        """Cria resposta de token para um usuário válido.

        O `sub` do token recebe o UUID do usuário como string. Essa escolha deixa
        o JWT simples e evita serialização customizada de UUID.
        """

        settings = get_settings()
        access_token = create_access_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
