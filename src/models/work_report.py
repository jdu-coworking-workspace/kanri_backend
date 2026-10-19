from enum import Enum

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
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


class ReportType(str, Enum):
    """API: hourly, output. PostgreSQL `reporttype` nomlarni saqlaydi: HOURLY, OUTPUT."""

    HOURLY = "hourly"  # start/finish asosidagi hisobot
    OUTPUT = "output"  # 成果制: ish vaqti + [条件1/2] soni

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
    def parse(cls, value) -> "ReportType":
        parsed = cls.try_parse(value)
        if parsed is None:
            raise ValueError(f"Unknown report type: {value!r}")
        return parsed


def _report_status_db_values(enum_cls):
    return [member.name for member in enum_cls]


def _report_type_db_values(enum_cls):
    return [member.name for member in enum_cls]


class MonthlyReport(Base, TimeStampsMixin):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "year",
            "month",
            "title",
            name="uq_monthly_reports_student_period_title",
        ),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_monthly_reports_month"),
        Index("ix_monthly_reports_student_period", "student_id", "year", "month"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    report_type = Column(
        SQLEnum(
            ReportType,
            name="reporttype",
            native_enum=True,
            values_callable=_report_type_db_values,
            validate_strings=True,
        ),
        nullable=False,
        default=ReportType.HOURLY,
        server_default="HOURLY",
    )
    # output start
    condition_1_label = Column(String(100), nullable=True)
    condition_2_label = Column(String(100), nullable=True)
    unit_price_1 = Column(Integer, nullable=True)
    unit_price_2 = Column(Integer, nullable=True)
    # end
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
    # output report uchun quyidagi maydonlar ishlatiladi:
    work_minutes = Column(Integer, nullable=True)
    count_1 = Column(Integer, nullable=True)
    count_2 = Column(Integer, nullable=True)
    is_approved = Column(Boolean, nullable=True)
    approved_count_1 = Column(Integer, nullable=True)
    approved_count_2 = Column(Integer, nullable=True)

    monthly_report = relationship("MonthlyReport", back_populates="days")
