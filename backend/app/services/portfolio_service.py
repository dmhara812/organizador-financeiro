from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.enums import AssetType, TransactionType
from app.models.transaction import Transaction
from app.repositories import (
    AssetPriceRepository,
    AssetRepository,
    TransactionRepository,
)
from app.services.base import BaseService

ZERO = Decimal("0")
HUNDRED = Decimal("100")

ValuationSource = Literal["latest_price", "cost_basis_fallback", "none"]

INCREASE_POSITION_TYPES = {
    TransactionType.BUY,
    TransactionType.TRANSFER_IN,
}

DECREASE_POSITION_TYPES = {
    TransactionType.SELL,
    TransactionType.TRANSFER_OUT,
}


@dataclass(slots=True)
class PositionCalculationState:
    """Estado mutável usado apenas durante o cálculo de uma posição.

    Essa classe não é retornada pela API. Ela existe para deixar a regra de
    custo médio mais legível e evitar trabalhar com dicionários soltos dentro do
    service.
    """

    quantity: Decimal = ZERO
    cost_basis: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class AssetPosition:
    """Resultado calculado para a posição atual de um ativo."""

    asset_id: UUID
    symbol: str
    name: str
    asset_type: AssetType
    category_id: UUID | None
    currency: str
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    latest_price: Decimal | None
    latest_price_date: date | None
    market_value: Decimal
    unrealized_result: Decimal
    unrealized_result_percent: Decimal | None
    valuation_source: ValuationSource


@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    """Fatia de alocação usada em gráficos do dashboard."""

    group_key: str
    label: str
    amount: Decimal
    percentage: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioCashFlowSummary:
    """Resumo de fluxos financeiros do usuário em um período."""

    total_deposited: Decimal
    total_withdrawn: Decimal
    total_dividends: Decimal
    total_interest: Decimal
    total_fees: Decimal
    total_taxes: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """Resumo consolidado que será usado pelo dashboard."""

    total_market_value: Decimal
    total_cost_basis: Decimal
    unrealized_result: Decimal
    unrealized_result_percent: Decimal | None
    cash_flow: PortfolioCashFlowSummary
    positions: list[AssetPosition]
    allocation_by_asset_type: list[PortfolioAllocation]
    allocation_by_currency: list[PortfolioAllocation]


class PortfolioService(BaseService):
    """Service responsável por cálculos financeiros de leitura.

    O projeto usa movimentações como fonte da verdade. Por isso, este service
    recalcula posição e valor consolidado a partir de transações e preços, em
    vez de depender de uma tabela de saldo que poderia ficar desatualizada.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.asset_repository = AssetRepository(db=db)
        self.asset_price_repository = AssetPriceRepository(db=db)
        self.transaction_repository = TransactionRepository(db=db)

    def calculate_available_quantity(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        occurred_to: datetime | None = None,
        exclude_transaction_id: UUID | None = None,
    ) -> Decimal:
        """Calcula a quantidade disponível de um ativo.

        `exclude_transaction_id` permite validar atualização de movimentações.
        Sem esse parâmetro, uma venda em edição seria considerada no próprio
        cálculo de disponibilidade, podendo gerar falso bloqueio.
        """

        transactions = self.transaction_repository.list_asset_transactions_for_position(
            user_id=user_id,
            asset_id=asset_id,
            occurred_to=occurred_to,
            exclude_transaction_id=exclude_transaction_id,
        )
        state = self._calculate_position_state(transactions)
        return state.quantity

    def list_positions(
        self,
        *,
        user_id: UUID,
        occurred_to: datetime | None = None,
    ) -> list[AssetPosition]:
        """Lista posições abertas do usuário.

        Apenas ativos com quantidade positiva entram no resultado. Ativos sem
        posição aberta continuam cadastrados, mas não devem aparecer como parte
        do patrimônio atual.
        """

        assets_by_id = self._get_assets_by_id(user_id=user_id)
        transactions_by_asset_id = self._get_position_transactions_by_asset_id(
            user_id=user_id,
            occurred_to=occurred_to,
        )
        latest_prices_by_asset_id = self._get_latest_prices_by_asset_id(
            user_id=user_id,
        )

        positions: list[AssetPosition] = []

        for asset_id, transactions in transactions_by_asset_id.items():
            asset = assets_by_id.get(asset_id)
            if asset is None:
                continue

            position = self._build_asset_position(
                asset=asset,
                transactions=transactions,
                latest_price=latest_prices_by_asset_id.get(asset_id),
            )
            if position is not None:
                positions.append(position)

        return sorted(positions, key=lambda position: position.symbol)

    def get_summary(
        self,
        *,
        user_id: UUID,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> PortfolioSummary:
        """Monta um resumo financeiro inicial para o dashboard.

        `occurred_from` afeta apenas o resumo de fluxos, como aportes e
        dividendos. A posição patrimonial usa todas as movimentações até
        `occurred_to`, porque uma carteira atual depende do histórico completo.
        """

        positions = self.list_positions(user_id=user_id, occurred_to=occurred_to)
        cash_flow_transactions = self.transaction_repository.list_by_user_for_summary(
            user_id=user_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        cash_flow = self._calculate_cash_flow_summary(cash_flow_transactions)

        total_market_value = sum(
            (position.market_value for position in positions),
            ZERO,
        )
        total_cost_basis = sum(
            (position.cost_basis for position in positions),
            ZERO,
        )
        unrealized_result = total_market_value - total_cost_basis

        return PortfolioSummary(
            total_market_value=total_market_value,
            total_cost_basis=total_cost_basis,
            unrealized_result=unrealized_result,
            unrealized_result_percent=self._calculate_percentage(
                numerator=unrealized_result,
                denominator=total_cost_basis,
            ),
            cash_flow=cash_flow,
            positions=positions,
            allocation_by_asset_type=self._build_allocation_by_asset_type(
                positions=positions,
                total_market_value=total_market_value,
            ),
            allocation_by_currency=self._build_allocation_by_currency(
                positions=positions,
                total_market_value=total_market_value,
            ),
        )

    def _get_assets_by_id(self, *, user_id: UUID) -> dict[UUID, Asset]:
        """Carrega ativos do usuário em um dicionário por id."""

        assets = self.asset_repository.list_all_by_user(user_id=user_id)
        return {asset.id: asset for asset in assets}

    def _get_latest_prices_by_asset_id(
        self,
        *,
        user_id: UUID,
    ) -> dict[UUID, AssetPrice]:
        """Carrega o preço mais recente de cada ativo do usuário."""

        prices = self.asset_price_repository.list_latest_by_user(user_id=user_id)
        return {price.asset_id: price for price in prices}

    def _get_position_transactions_by_asset_id(
        self,
        *,
        user_id: UUID,
        occurred_to: datetime | None,
    ) -> dict[UUID, list[Transaction]]:
        """Agrupa movimentações de posição por ativo."""

        transactions = self.transaction_repository.list_asset_transactions_for_position(
            user_id=user_id,
            occurred_to=occurred_to,
        )
        grouped_transactions: dict[UUID, list[Transaction]] = defaultdict(list)

        for transaction in transactions:
            if transaction.asset_id is None:
                continue

            grouped_transactions[transaction.asset_id].append(transaction)

        return grouped_transactions

    def _build_asset_position(
        self,
        *,
        asset: Asset,
        transactions: list[Transaction],
        latest_price: AssetPrice | None,
    ) -> AssetPosition | None:
        """Calcula posição, custo e valor de mercado de um ativo."""

        state = self._calculate_position_state(transactions)
        if state.quantity <= ZERO:
            return None

        latest_price_value = latest_price.price if latest_price is not None else None
        latest_price_date = (
            latest_price.price_date if latest_price is not None else None
        )
        market_value, valuation_source = self._calculate_market_value(
            quantity=state.quantity,
            cost_basis=state.cost_basis,
            latest_price=latest_price_value,
        )
        unrealized_result = market_value - state.cost_basis

        return AssetPosition(
            asset_id=asset.id,
            symbol=asset.symbol,
            name=asset.name,
            asset_type=asset.asset_type,
            category_id=asset.category_id,
            currency=asset.currency,
            quantity=state.quantity,
            average_cost=self._calculate_average_cost(
                cost_basis=state.cost_basis,
                quantity=state.quantity,
            ),
            cost_basis=state.cost_basis,
            latest_price=latest_price_value,
            latest_price_date=latest_price_date,
            market_value=market_value,
            unrealized_result=unrealized_result,
            unrealized_result_percent=self._calculate_percentage(
                numerator=unrealized_result,
                denominator=state.cost_basis,
            ),
            valuation_source=valuation_source,
        )

    def _calculate_position_state(
        self,
        transactions: list[Transaction],
    ) -> PositionCalculationState:
        """Calcula quantidade e custo em aberto a partir das movimentações."""

        state = PositionCalculationState()

        for transaction in transactions:
            transaction_type = transaction.transaction_type

            if transaction_type in INCREASE_POSITION_TYPES:
                self._apply_position_increase(state=state, transaction=transaction)
                continue

            if transaction_type in DECREASE_POSITION_TYPES:
                self._apply_position_decrease(state=state, transaction=transaction)

        return state

    def _apply_position_increase(
        self,
        *,
        state: PositionCalculationState,
        transaction: Transaction,
    ) -> None:
        """Aplica compra ou transferência de entrada na posição."""

        quantity = self._get_transaction_quantity(transaction)
        if quantity <= ZERO:
            return

        state.quantity += quantity
        state.cost_basis += transaction.net_amount

    def _apply_position_decrease(
        self,
        *,
        state: PositionCalculationState,
        transaction: Transaction,
    ) -> None:
        """Aplica venda ou transferência de saída na posição.

        Removemos o custo proporcional pelo custo médio anterior à saída. Caso
        os dados tenham uma venda maior do que a posição, limitamos a baixa ao
        saldo disponível para não gerar custo negativo no dashboard.
        """

        quantity = self._get_transaction_quantity(transaction)
        if quantity <= ZERO or state.quantity <= ZERO:
            return

        quantity_to_remove = min(quantity, state.quantity)
        average_cost = self._calculate_average_cost(
            cost_basis=state.cost_basis,
            quantity=state.quantity,
        )

        state.quantity -= quantity_to_remove
        state.cost_basis -= average_cost * quantity_to_remove

        if state.quantity <= ZERO:
            state.quantity = ZERO
            state.cost_basis = ZERO

    @staticmethod
    def _get_transaction_quantity(transaction: Transaction) -> Decimal:
        """Retorna quantidade da movimentação ou zero quando não houver."""

        return transaction.quantity or ZERO

    @staticmethod
    def _calculate_average_cost(*, cost_basis: Decimal, quantity: Decimal) -> Decimal:
        """Calcula custo médio evitando divisão por zero."""

        if quantity <= ZERO:
            return ZERO

        return cost_basis / quantity

    @staticmethod
    def _calculate_market_value(
        *,
        quantity: Decimal,
        cost_basis: Decimal,
        latest_price: Decimal | None,
    ) -> tuple[Decimal, ValuationSource]:
        """Calcula valor de mercado e informa a origem da avaliação."""

        if latest_price is not None:
            return quantity * latest_price, "latest_price"

        if cost_basis > ZERO:
            return cost_basis, "cost_basis_fallback"

        return ZERO, "none"

    def _calculate_cash_flow_summary(
        self,
        transactions: list[Transaction],
    ) -> PortfolioCashFlowSummary:
        """Soma fluxos financeiros relevantes para o dashboard."""

        total_deposited = ZERO
        total_withdrawn = ZERO
        total_dividends = ZERO
        total_interest = ZERO
        total_fees = ZERO
        total_taxes = ZERO

        for transaction in transactions:
            amount = transaction.net_amount
            transaction_type = transaction.transaction_type

            if transaction_type == TransactionType.CASH_DEPOSIT:
                total_deposited += amount
            elif transaction_type == TransactionType.CASH_WITHDRAWAL:
                total_withdrawn += amount
            elif transaction_type == TransactionType.DIVIDEND:
                total_dividends += amount
            elif transaction_type == TransactionType.INTEREST:
                total_interest += amount
            elif transaction_type == TransactionType.FEE:
                total_fees += amount
            elif transaction_type == TransactionType.TAX:
                total_taxes += amount

        return PortfolioCashFlowSummary(
            total_deposited=total_deposited,
            total_withdrawn=total_withdrawn,
            total_dividends=total_dividends,
            total_interest=total_interest,
            total_fees=total_fees,
            total_taxes=total_taxes,
        )

    def _build_allocation_by_asset_type(
        self,
        *,
        positions: list[AssetPosition],
        total_market_value: Decimal,
    ) -> list[PortfolioAllocation]:
        """Agrupa valor de mercado por tipo de ativo."""

        grouped_values: dict[AssetType, Decimal] = defaultdict(lambda: ZERO)

        for position in positions:
            if position.market_value > ZERO:
                grouped_values[position.asset_type] += position.market_value

        return [
            PortfolioAllocation(
                group_key=asset_type.value,
                label=asset_type.value,
                amount=amount,
                percentage=self._calculate_percentage(
                    numerator=amount,
                    denominator=total_market_value,
                ),
            )
            for asset_type, amount in sorted(
                grouped_values.items(),
                key=lambda item: item[0].value,
            )
        ]

    def _build_allocation_by_currency(
        self,
        *,
        positions: list[AssetPosition],
        total_market_value: Decimal,
    ) -> list[PortfolioAllocation]:
        """Agrupa valor de mercado por moeda."""

        grouped_values: dict[str, Decimal] = defaultdict(lambda: ZERO)

        for position in positions:
            if position.market_value > ZERO:
                grouped_values[position.currency] += position.market_value

        return [
            PortfolioAllocation(
                group_key=currency,
                label=currency,
                amount=amount,
                percentage=self._calculate_percentage(
                    numerator=amount,
                    denominator=total_market_value,
                ),
            )
            for currency, amount in sorted(grouped_values.items())
        ]

    @staticmethod
    def _calculate_percentage(
        *,
        numerator: Decimal,
        denominator: Decimal,
    ) -> Decimal | None:
        """Calcula percentual com segurança contra divisão por zero."""

        if denominator == ZERO:
            return None

        return (numerator / denominator) * HUNDRED
