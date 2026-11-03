"""report type and output fields

Revision ID: 58ccb52222ff
Revises: 21b3766ba6d8
Create Date: 2026-10-17 14:27:44.580969

"""

from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "58ccb52222ff"
down_revision: Union[str, Sequence[str], None] = "21b3766ba6d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    postgresql.ENUM("HOURLY", "OUTPUT", name="reporttype").create(
        op.get_bind(), checkfirst=True
    )
    op.add_column(
        "monthly_reports",
        sa.Column(
            "report_type",
            postgresql.ENUM("HOURLY", "OUTPUT", name="reporttype", create_type=False),
            nullable=False,
            server_default="HOURLY",
        ),
    )
    op.add_column(
        "monthly_reports", sa.Column("cowork_no", sa.String(50), nullable=True)
    )
    op.add_column(
        "monthly_reports", sa.Column("condition_1_label", sa.String(100), nullable=True)
    )
    op.add_column(
        "monthly_reports", sa.Column("condition_2_label", sa.String(100), nullable=True)
    )
    op.add_column(
        "monthly_reports", sa.Column("unit_price_1", sa.Integer(), nullable=True)
    )
    op.add_column(
        "monthly_reports", sa.Column("unit_price_2", sa.Integer(), nullable=True)
    )

    op.add_column(
        "daily_reports", sa.Column("work_minutes", sa.Integer(), nullable=True)
    )
    op.add_column("daily_reports", sa.Column("count_1", sa.Integer(), nullable=True))
    op.add_column("daily_reports", sa.Column("count_2", sa.Integer(), nullable=True))
    op.add_column(
        "daily_reports", sa.Column("is_approved", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "daily_reports", sa.Column("approved_count_1", sa.Integer(), nullable=True)
    )
    op.add_column(
        "daily_reports", sa.Column("approved_count_2", sa.Integer(), nullable=True)
    )


def downgrade():
    for col in (
        "approved_count_2",
        "approved_count_1",
        "is_approved",
        "count_2",
        "count_1",
        "work_minutes",
    ):
        op.drop_column("daily_reports", col)
    for col in (
        "unit_price_2",
        "unit_price_1",
        "condition_2_label",
        "condition_1_label",
        "cowork_no",
        "report_type",
    ):
        op.drop_column("monthly_reports", col)
    postgresql.ENUM(name="reporttype").drop(op.get_bind(), checkfirst=True)
