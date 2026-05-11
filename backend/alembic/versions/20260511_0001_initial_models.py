"""initial models

Revision ID: 20260511_0001
Revises:
Create Date: 2026-05-11 00:01:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260511_0001"
down_revision = None
branch_labels = None
depends_on = None


asset_type_enum = postgresql.ENUM(
    "stock",
    "reit",
    "etf",
    "fixed_income",
    "crypto",
    "cash",
    "other",
    name="asset_type",
    create_type=False,
)
transaction_type_enum = postgresql.ENUM(
    "buy",
    "sell",
    "cash_deposit",
    "cash_withdrawal",
    "dividend",
    "interest",
    "fee",
    "tax",
    "transfer_in",
    "transfer_out",
    name="transaction_type",
    create_type=False,
)
price_source_enum = postgresql.ENUM(
    "manual",
    "csv_import",
    "api",
    name="price_source",
    create_type=False,
)


def upgrade() -> None:
    """Cria o schema inicial do domínio financeiro.

    Os enums são criados explicitamente para que o downgrade consiga removê-los
    de forma previsível após excluir as tabelas que dependem deles.
    """

    bind = op.get_bind()
    asset_type_enum.create(bind, checkfirst=True)
    transaction_type_enum.create(bind, checkfirst=True)
    price_source_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True
    )

    op.create_table(
        "categories",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    )
    op.create_index(
        op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False
    )

    op.create_table(
        "brokerages",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_brokerages_user_name"),
    )
    op.create_index(
        op.f("ix_brokerages_user_id"), "brokerages", ["user_id"], unique=False
    )

    op.create_table(
        "assets",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("exchange", sa.String(length=40), nullable=True),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "symbol", "asset_type", name="uq_assets_user_symbol_type"
        ),
    )
    op.create_index(
        "ix_assets_user_type", "assets", ["user_id", "asset_type"], unique=False
    )
    op.create_index(
        op.f("ix_assets_category_id"), "assets", ["category_id"], unique=False
    )
    op.create_index(op.f("ix_assets_user_id"), "assets", ["user_id"], unique=False)

    op.create_table(
        "asset_prices",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", price_source_enum, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3", name="ck_asset_prices_currency_length"
        ),
        sa.CheckConstraint("price > 0", name="ck_asset_prices_price_positive"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "asset_id", "price_date", name="uq_asset_prices_user_asset_date"
        ),
    )
    op.create_index(
        "ix_asset_prices_asset_date",
        "asset_prices",
        ["asset_id", "price_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_prices_asset_id"), "asset_prices", ["asset_id"], unique=False
    )
    op.create_index(
        op.f("ix_asset_prices_user_id"), "asset_prices", ["user_id"], unique=False
    )

    op.create_table(
        "transactions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("brokerage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", transaction_type_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("net_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_reference", sa.String(length=120), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3", name="ck_transactions_currency_length"
        ),
        sa.CheckConstraint(
            "fee_amount >= 0", name="ck_transactions_fee_amount_non_negative"
        ),
        sa.CheckConstraint(
            "gross_amount >= 0", name="ck_transactions_gross_amount_non_negative"
        ),
        sa.CheckConstraint(
            "net_amount >= 0", name="ck_transactions_net_amount_non_negative"
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_transactions_quantity_positive"
        ),
        sa.CheckConstraint(
            "tax_amount >= 0", name="ck_transactions_tax_amount_non_negative"
        ),
        sa.CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0",
            name="ck_transactions_unit_price_non_negative",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["brokerage_id"], ["brokerages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transactions_asset_occurred_at",
        "transactions",
        ["asset_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_user_occurred_at",
        "transactions",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_user_type",
        "transactions",
        ["user_id", "transaction_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_asset_id"), "transactions", ["asset_id"], unique=False
    )
    op.create_index(
        op.f("ix_transactions_brokerage_id"),
        "transactions",
        ["brokerage_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Remove o schema inicial na ordem inversa das dependências."""

    bind = op.get_bind()

    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_brokerage_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_asset_id"), table_name="transactions")
    op.drop_index("ix_transactions_user_type", table_name="transactions")
    op.drop_index("ix_transactions_user_occurred_at", table_name="transactions")
    op.drop_index("ix_transactions_asset_occurred_at", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_asset_prices_user_id"), table_name="asset_prices")
    op.drop_index(op.f("ix_asset_prices_asset_id"), table_name="asset_prices")
    op.drop_index("ix_asset_prices_asset_date", table_name="asset_prices")
    op.drop_table("asset_prices")

    op.drop_index(op.f("ix_assets_user_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_category_id"), table_name="assets")
    op.drop_index("ix_assets_user_type", table_name="assets")
    op.drop_table("assets")

    op.drop_index(op.f("ix_brokerages_user_id"), table_name="brokerages")
    op.drop_table("brokerages")

    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_table("users")

    price_source_enum.drop(bind, checkfirst=True)
    transaction_type_enum.drop(bind, checkfirst=True)
    asset_type_enum.drop(bind, checkfirst=True)
