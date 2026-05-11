"""Exporta os models para uso pela aplicação e pelo Alembic.

O Alembic precisa que todos os models sejam importados antes de acessar
`Base.metadata`. Sem esses imports, a autogeração de migrations pode criar
arquivos incompletos por não conhecer todas as tabelas.
"""

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.base import Base
from app.models.brokerage import Brokerage
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "Asset",
    "AssetPrice",
    "Base",
    "Brokerage",
    "Category",
    "Transaction",
    "User",
]
