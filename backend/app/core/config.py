from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da aplicação.

    Centralizar as configurações evita valores fixos espalhados pelo código e
    facilita alternar entre ambiente local, testes, Docker e produção. O arquivo
    `.env` é útil localmente, enquanto em produção as mesmas chaves podem ser
    fornecidas diretamente pela plataforma de deploy.
    """

    app_name: str = "Finance Investment Organizer API"
    app_version: str = "0.1.0"
    environment: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    postgres_server: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "finance_user"
    postgres_password: str = "finance_password"
    postgres_db: str = "finance_app"
    database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Retorna a URL de conexão usada pelo SQLAlchemy.

        A aplicação aceita `DATABASE_URL` pronta para facilitar deploy em
        plataformas que fornecem a string completa. Quando essa variável não é
        informada, a URL é montada a partir das variáveis individuais do
        PostgreSQL, o que deixa o ambiente Docker local mais explícito.
        """

        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_server}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Carrega configurações uma única vez durante o ciclo de vida da aplicação.

    O cache evita reler o `.env` a cada request. Em testes futuros, esse cache
    poderá ser limpo para sobrescrever configurações de forma controlada.
    """

    return Settings()
