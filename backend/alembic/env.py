from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Garante que `app` seja importável quando o Alembic roda a partir da pasta
# `backend`. Isso mantém o comando simples dentro e fora do Docker.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# O metadata precisa conter todos os models importados em app.models.__init__.
# É isso que permite ao Alembic comparar models e banco em revisões futuras.
target_metadata = Base.metadata


def get_database_url() -> str:
    """Obtém a mesma URL de banco usada pela aplicação FastAPI.

    Usar a configuração centralizada evita divergência entre o banco acessado em
    runtime e o banco usado nas migrations.
    """

    return get_settings().sqlalchemy_database_uri


def run_migrations_offline() -> None:
    """Executa migrations sem abrir conexão ativa com o banco.

    Esse modo é útil para gerar SQL, embora o fluxo principal do projeto use o
    modo online via Docker Compose.
    """

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrations conectando diretamente ao PostgreSQL.

    `pool.NullPool` evita manter conexões abertas após comandos de migration,
    o que é adequado para execuções pontuais no container ou em pipelines.
    """

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
