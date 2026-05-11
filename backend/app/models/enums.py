from enum import Enum


class AssetType(str, Enum):
    """Tipos de ativo suportados no escopo inicial.

    Os valores ficam em minúsculas porque serão persistidos no PostgreSQL e
    expostos futuramente pela API. Isso evita conversões desnecessárias entre
    banco, backend e frontend.
    """

    STOCK = "stock"
    REIT = "reit"
    ETF = "etf"
    FIXED_INCOME = "fixed_income"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class TransactionType(str, Enum):
    """Tipos de movimentação financeira do produto.

    Compras e vendas afetam posição de ativos. Depósitos, retiradas, taxas,
    impostos e rendimentos registram fluxo financeiro e permitem calcular
    aportes e performance sem criar tabelas paralelas de saldo nesta etapa.
    """

    BUY = "buy"
    SELL = "sell"
    CASH_DEPOSIT = "cash_deposit"
    CASH_WITHDRAWAL = "cash_withdrawal"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    TAX = "tax"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class PriceSource(str, Enum):
    """Origem do preço usado para avaliação dos ativos.

    A origem será importante para distinguir preços digitados manualmente,
    importados por CSV ou obtidos por integração externa em funcionalidades
    avançadas.
    """

    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    API = "api"


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Retorna os valores persistíveis de um enum.

    SQLAlchemy, por padrão, pode persistir nomes dos membros. Usar os valores
    explicitamente mantém o banco alinhado ao contrato esperado pela API.
    """

    return [member.value for member in enum_class]
