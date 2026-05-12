from __future__ import annotations

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import AppBaseModel, BaseReadSchema


class UserBase(AppBaseModel):
    """Campos públicos do usuário usados em entrada e saída da API."""

    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normaliza e-mail antes de persistir ou comparar.

        O banco já terá índice único case-insensitive, mas normalizar na borda
        da API reduz diferenças visuais e simplifica autenticação futura.
        """

        return str(value).strip().lower()


class UserCreate(UserBase):
    """Payload de criação de usuário.

    A senha aparece apenas em schema de entrada. Na Etapa 6, o service de
    autenticação transformará esse valor em hash antes de salvar no banco.
    """

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Aplica uma regra mínima de senha para o cadastro."""

        has_letter = any(char.isalpha() for char in value)
        has_number = any(char.isdigit() for char in value)
        if not has_letter or not has_number:
            raise ValueError("A senha deve conter pelo menos uma letra e um número.")
        return value


class UserUpdate(AppBaseModel):
    """Payload de atualização parcial de perfil.

    Atualização de senha ficará separada na etapa de autenticação para permitir
    regras próprias, como senha atual obrigatória.
    """

    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    is_active: bool | None = None


class UserRead(BaseReadSchema):
    """Resposta segura de usuário sem expor `hashed_password`."""

    email: EmailStr
    full_name: str
    is_active: bool
