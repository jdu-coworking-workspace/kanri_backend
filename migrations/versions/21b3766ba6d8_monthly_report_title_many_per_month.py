"""monthly report title, many per month

Revision ID: 21b3766ba6d8
Revises: c8d9e0f1a2b3
Create Date: 2026-10-16 14:37:32.601157

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "21b3766ba6d8"
down_revision: Union[str, Sequence[str], None] = "243352baee4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Mavjud reportlar uchun vaqtincha default nom beramiz
    op.add_column(
        "monthly_reports",
        sa.Column("title", sa.String(255), nullable=False, server_default="Hisobot"),
    )
    op.alter_column("monthly_reports", "title", server_default=None)

    op.drop_constraint(
        "uq_monthly_reports_student_period", "monthly_reports", type_="unique"
    )
    op.create_unique_constraint(
        "uq_monthly_reports_student_period_title",
        "monthly_reports",
        ["student_id", "year", "month", "title"],
    )
    op.create_index(
        "ix_monthly_reports_student_period",
        "monthly_reports",
        ["student_id", "year", "month"],
    )


def downgrade():
    op.drop_index("ix_monthly_reports_student_period", table_name="monthly_reports")
    op.drop_constraint(
        "uq_monthly_reports_student_period_title", "monthly_reports", type_="unique"
    )
    op.create_unique_constraint(
        "uq_monthly_reports_student_period",
        "monthly_reports",
        ["student_id", "year", "month"],
    )
    op.drop_column("monthly_reports", "title")
