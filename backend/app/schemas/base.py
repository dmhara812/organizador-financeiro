from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Base única para os schemas Pydantic da aplicação.

    `from_attributes=True` permite montar respostas a partir de objetos
    SQLAlchemy sem acoplar rotas aos models. `str_strip_whitespace=True`
    remove espaços desnecessários em entradas textuais, reduzindo validações
    repetidas nos schemas específicos das próximas etapas.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class IDSchema(AppBaseModel):
    """Contrato reutilizável para entidades expostas pela API com UUID.

    O projeto usa UUID nos models para não expor sequências internas do banco.
    Manter esse schema separado facilita compor respostas de leitura.
    """

    id: UUID


class TimestampSchema(AppBaseModel):
    """Contrato reutilizável para campos de auditoria básica.

    Os timestamps vêm dos mixins SQLAlchemy. Expor esses campos nas respostas
    ajuda o frontend e também melhora a rastreabilidade em ambiente de portfólio.
    """

    created_at: datetime
    updated_at: datetime


class BaseReadSchema(IDSchema, TimestampSchema):
    """Base para schemas de leitura de entidades persistidas.

    As próximas etapas poderão herdar desta classe em respostas como
    `AssetRead`, `CategoryRead` e `TransactionRead`, evitando repetição de
    `id`, `created_at` e `updated_at`.
    """
