from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    future=True,
)
"""Engine global do SQLAlchemy.

`pool_pre_ping=True` verifica se a conexão ainda está ativa antes de reutilizar
uma conexão do pool. Isso reduz erros comuns quando o banco reinicia ou quando
uma conexão fica ociosa por muito tempo, especialmente em Docker e deploy.
"""

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
"""Fábrica de sessões do banco.

`expire_on_commit=False` evita que objetos retornados pela camada de serviço
percam seus atributos imediatamente após commit. Essa decisão simplifica o uso
com schemas Pydantic nas próximas etapas.
"""


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco por request.

    A sessão é aberta quando a rota precisa do banco e sempre fechada ao final,
    mesmo se ocorrer uma exceção. Esse padrão evita vazamento de conexões e será
    reutilizado por repositories e services nas próximas etapas.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
