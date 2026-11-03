"""add image url to projects

Revision ID: 4e5f6a7b8c9d
Revises: 38d591278549
Create Date: 2026-10-24 20:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4e5f6a7b8c9d"
down_revision: Union[str, Sequence[str], None] = "38d591278549"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("image_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "image_url")
