"""drop student point_1 point_2 point_3 columns

Revision ID: a1b2c3d4e5f6
Revises: 059803ad9402
Create Date: 2026-09-22 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "059803ad9402"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("students", "point_1")
    op.drop_column("students", "point_2")
    op.drop_column("students", "point_3")


def downgrade() -> None:
    op.add_column("students", sa.Column("point_1", sa.Integer(), nullable=True))
    op.add_column("students", sa.Column("point_2", sa.Integer(), nullable=True))
    op.add_column("students", sa.Column("point_3", sa.Integer(), nullable=True))
