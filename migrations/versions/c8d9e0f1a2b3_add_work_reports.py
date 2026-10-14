"""add monthly and daily work reports

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-27 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


report_status = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "APPROVED",
    "REJECTED",
    name="reportstatus",
    create_type=False,
)


def upgrade() -> None:
    report_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "monthly_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("status", report_status, nullable=False),
        sa.Column("week_1", sa.Text(), nullable=True),
        sa.Column("week_2", sa.Text(), nullable=True),
        sa.Column("week_3", sa.Text(), nullable=True),
        sa.Column("week_4", sa.Text(), nullable=True),
        sa.Column("week_5", sa.Text(), nullable=True),
        sa.Column("stipend_amount", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "student_id", "year", "month", name="uq_monthly_reports_student_period"
        ),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_monthly_reports_month"),
    )
    op.create_index("ix_monthly_reports_student_id", "monthly_reports", ["student_id"])
    op.create_index("ix_monthly_reports_period", "monthly_reports", ["year", "month"])

    op.create_table(
        "daily_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("monthly_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("finish_time", sa.Time(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_day_off", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["monthly_report_id"], ["monthly_reports.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "monthly_report_id", "work_date", name="uq_daily_reports_month_date"
        ),
    )
    op.create_index(
        "ix_daily_reports_monthly_report_id", "daily_reports", ["monthly_report_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_daily_reports_monthly_report_id", table_name="daily_reports")
    op.drop_table("daily_reports")
    op.drop_index("ix_monthly_reports_period", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_student_id", table_name="monthly_reports")
    op.drop_table("monthly_reports")
    report_status.drop(op.get_bind(), checkfirst=True)
