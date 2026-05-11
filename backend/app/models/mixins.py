from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adiciona chave primária UUID às entidades principais.

    UUIDs evitam expor sequências internas em endpoints públicos e facilitam
    integrações futuras, como importações ou sincronização entre ambientes.
    """

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    """Adiciona timestamps padronizados para auditoria básica.

    `server_default=func.now()` deixa o banco preencher a data quando registros
    forem criados fora da aplicação. `onupdate` mantém `updated_at` útil para
    alterações feitas pelo ORM nas próximas etapas.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
