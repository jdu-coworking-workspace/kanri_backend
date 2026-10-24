"""add graduated semester enum value

Revision ID: 5f6a7b8c9d0e
Revises: 4e5f6a7b8c9d
Create Date: 2026-10-24 21:08:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5f6a7b8c9d0e"
down_revision: Union[str, Sequence[str], None] = "4e5f6a7b8c9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE semesterenum ADD VALUE IF NOT EXISTS 'GRADUATED'")


def downgrade() -> None:
    # PostgreSQL does not support removing an enum value safely in place.
    pass
