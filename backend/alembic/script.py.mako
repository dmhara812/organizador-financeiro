"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Aplica as mudanças desta revisão."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reverte as mudanças desta revisão."""
    ${downgrades if downgrades else "pass"}