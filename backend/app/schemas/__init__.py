from app.schemas.asset import AssetBase, AssetCreate, AssetRead, AssetUpdate
from app.schemas.asset_price import (
    AssetPriceBase,
    AssetPriceCreate,
    AssetPriceRead,
    AssetPriceUpdate,
)
from app.schemas.base import AppBaseModel, BaseReadSchema, IDSchema, TimestampSchema
from app.schemas.brokerage import (
    BrokerageBase,
    BrokerageCreate,
    BrokerageRead,
    BrokerageUpdate,
)
from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)
from app.schemas.common import ErrorDetail, ErrorResponse, MessageResponse
from app.schemas.enums import AssetType, PriceSource, TransactionType
from app.schemas.filters import (
    AssetFilters,
    AssetPriceFilters,
    BrokerageFilters,
    CategoryFilters,
    TransactionFilters,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)
from app.schemas.user import UserBase, UserCreate, UserRead, UserUpdate

# Este arquivo reexporta os contratos principais para simplificar imports nas
# rotas futuras. A lista deve conter apenas nomes importados acima; isso evita
# erros do Ruff como F821 Undefined name e facilita revisar o contrato público
# do pacote `app.schemas`.
__all__ = [
    "AppBaseModel",
    "AssetBase",
    "AssetCreate",
    "AssetFilters",
    "AssetPriceBase",
    "AssetPriceCreate",
    "AssetPriceFilters",
    "AssetPriceRead",
    "AssetPriceUpdate",
    "AssetRead",
    "AssetType",
    "AssetUpdate",
    "BaseReadSchema",
    "BrokerageBase",
    "BrokerageCreate",
    "BrokerageFilters",
    "BrokerageRead",
    "BrokerageUpdate",
    "CategoryBase",
    "CategoryCreate",
    "CategoryFilters",
    "CategoryRead",
    "CategoryUpdate",
    "ErrorDetail",
    "ErrorResponse",
    "IDSchema",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationParams",
    "PriceSource",
    "TimestampSchema",
    "TransactionBase",
    "TransactionCreate",
    "TransactionFilters",
    "TransactionRead",
    "TransactionType",
    "TransactionUpdate",
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
