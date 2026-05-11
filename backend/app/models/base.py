from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa única dos models SQLAlchemy.

    Manter uma única base evita que o Alembic enxergue metadados incompletos.
    Todos os models da aplicação devem herdar desta classe para que migrations
    futuras consigam comparar o estado do código com o estado do banco.
    """
