from pydantic import Field

from app.schemas.base import AppBaseModel


class MessageResponse(AppBaseModel):
    """Resposta simples para operações que não precisam devolver uma entidade.

    Esse contrato será útil para endpoints como logout lógico, confirmação de
    operação ou respostas administrativas futuras, mantendo um formato previsível.
    """

    message: str = Field(..., min_length=1)


class ErrorDetail(AppBaseModel):
    """Detalhe individual de erro de validação ou regra de negócio.

    `field` é opcional porque nem todo erro pertence a um campo específico.
    Por exemplo, uma regra como "usuário inativo" é global da requisição.
    """

    field: str | None = None
    message: str = Field(..., min_length=1)


class ErrorResponse(AppBaseModel):
    """Contrato padronizado para erros da API.

    O handler global será implementado na Etapa 4.3. Criar o contrato agora
    permite que rotas e testes futuros usem o mesmo formato desde o início.
    """

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    details: list[ErrorDetail] = Field(default_factory=list)
