from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import LoginRequest, RegisterResponse, TokenResponse
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
)
def register_user(
    data: UserCreate,
    auth_service: AuthServiceDep,
) -> RegisterResponse:
    """Cria usuário e já devolve token de acesso.

    O cadastro delega hashing de senha, validação de duplicidade e criação do
    token ao `AuthService`. A rota fica responsável apenas pelo contrato HTTP.
    """

    return auth_service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica usuário usando JSON",
)
def login(
    data: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Autentica usuário por JSON.

    Esta rota será usada pelo frontend React, que enviará `email` e `password`
    em JSON e guardará o access token para chamadas protegidas.
    """

    return auth_service.login(data)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Autentica usuário usando formulário OAuth2",
)
def login_with_oauth2_form(
    form_data: OAuth2FormDep,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Autentica usuário usando formulário OAuth2.

    O Swagger/OpenAPI envia os campos `username` e `password` nesse fluxo. Como
    nosso domínio usa e-mail, tratamos `username` como e-mail e reaproveitamos o
    mesmo `AuthService.login`, evitando duplicar regra de autenticação.
    """

    login_data = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )
    return auth_service.login(login_data)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retorna o usuário autenticado atual",
)
def read_current_user(current_user: CurrentUserDep) -> UserRead:
    """Retorna dados públicos do usuário autenticado.

    A dependência `CurrentUserDep` valida token, busca o usuário no banco e
    bloqueia contas inativas antes da rota ser executada.
    """

    return current_user
