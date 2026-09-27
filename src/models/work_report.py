from enum import Enum

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    Enum as SQLEnum,
)

# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

from .base import Base, TimeStampsMixin, generate_uuid


class ReportStatus(str, Enum):
    """API qiymatlari: draft, submitted, approved, rejected.

    PostgreSQL `reportstatus` enum esa nomlarni saqlaydi:
    DRAFT, SUBMITTED, APPROVED, REJECTED.
    """

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

    @classmethod
    def try_parse(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            key = value.strip().lower()
            for member in cls:
                if member.value == key or member.name.lower() == key:
                    return member
        return None

    @classmethod
    def parse(cls, value) -> "ReportStatus":
        parsed = cls.try_parse(value)
        if parsed is None:
            raise ValueError(f"Unknown report status: {value!r}")
        return parsed


def _report_status_db_values(enum_cls):
    return [member.name for member in enum_cls]


class MonthlyReport(Base, TimeStampsMixin):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "year", "month", name="uq_monthly_reports_student_period"
        ),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_monthly_reports_month"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year = Column(SmallInteger, nullable=False)
    month = Column(SmallInteger, nullable=False)
    status = Column(
        SQLEnum(
            ReportStatus,
            name="reportstatus",
            native_enum=True,
            values_callable=_report_status_db_values,
            validate_strings=True,
        ),
        nullable=False,
        default=ReportStatus.DRAFT,
    )
    week_1 = Column(Text, nullable=True)
    week_2 = Column(Text, nullable=True)
    week_3 = Column(Text, nullable=True)
    week_4 = Column(Text, nullable=True)
    week_5 = Column(Text, nullable=True)
    stipend_amount = Column(Integer, nullable=True)
    review_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    student = relationship("Student")
    days = relationship(
        "DailyReport",
        back_populates="monthly_report",
        cascade="all, delete-orphan",
    )


class DailyReport(Base, TimeStampsMixin):
    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint(
            "monthly_report_id", "work_date", name="uq_daily_reports_month_date"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    monthly_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monthly_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    finish_time = Column(Time, nullable=True)
    description = Column(Text, nullable=True)
    is_day_off = Column(Boolean, nullable=False, default=False)

    monthly_report = relationship("MonthlyReport", back_populates="days")
