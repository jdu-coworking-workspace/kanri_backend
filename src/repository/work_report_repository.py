from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload, selectinload

from src.models.student import Student
import calendar
from datetime import datetime, timedelta

from sqlalchemy import Float, Integer, String, and_, case, cast, exists, extract, func, or_, select

from src.models.project_member import ProjectMember
from src.models.work_report import DailyReport, MonthlyReport, ReportStatus, ReportType

def _minutes_of(col):
    return cast(extract("hour", col) * 60 + extract("minute", col), Integer)


_NOT_BLANK = func.length(func.btrim(DailyReport.description, " \t\r\n")) > 0
_IS_OUTPUT = MonthlyReport.report_type == ReportType.OUTPUT

_HOURLY_MINUTES = case(
    (
        or_(
            DailyReport.is_day_off.is_(True),
            DailyReport.start_time.is_(None),
            DailyReport.finish_time.is_(None),
        ),
        0,
    ),
    (_minutes_of(DailyReport.finish_time) < _minutes_of(DailyReport.start_time), 0),
    else_=_minutes_of(DailyReport.finish_time) - _minutes_of(DailyReport.start_time),
)
_OUTPUT_MINUTES = case(
    (DailyReport.is_day_off.is_(True), 0),
    else_=func.coalesce(DailyReport.work_minutes, 0),
)
_DAY_MINUTES = case((_IS_OUTPUT, _OUTPUT_MINUTES), else_=_HOURLY_MINUTES)

_HOURLY_COMPLETE = or_(
    DailyReport.is_day_off.is_(True),
    and_(
        DailyReport.start_time.is_not(None),
        DailyReport.finish_time.is_not(None),
        _NOT_BLANK,
        _HOURLY_MINUTES > 0,
    ),
)
_OUTPUT_COMPLETE = or_(
    DailyReport.is_day_off.is_(True),
    func.coalesce(DailyReport.work_minutes, 0) > 0,
)
_OUTPUT_HAS_DATA = or_(
    func.coalesce(DailyReport.work_minutes, 0) > 0,
    func.coalesce(DailyReport.count_1, 0) > 0,
    func.coalesce(DailyReport.count_2, 0) > 0,
    _NOT_BLANK,
)
_FILLED = case(
    (_IS_OUTPUT, case((and_(_OUTPUT_HAS_DATA, _OUTPUT_COMPLETE), 1), else_=0)),
    else_=case((_HOURLY_COMPLETE, 1), else_=0),
)
_ENTRY = case((and_(_IS_OUTPUT, _OUTPUT_HAS_DATA), 1), else_=0)

STATUS_NAMES = ("draft", "submitted", "approved", "rejected", "not_created")


def _student_scope() -> list:
    """Admin ro'yxatiga qaysi studentlar kirishi. Hozir hamma (graduated/on_leave ham).
    Keyin qoida o'zgarsa, shu yerga shart qo'shamiz."""
    return []

class WorkReportRepository:

    @staticmethod
    def get_by_id(db: Session, report_id: UUID) -> MonthlyReport | None:
        return (
            db.query(MonthlyReport)
            .options(
                joinedload(MonthlyReport.student),
                selectinload(MonthlyReport.days),
            )
            .filter(MonthlyReport.id == report_id)
            .first()
        )

    @staticmethod
    def get_by_student_period(
        db: Session, student_id: UUID, year: int, month: int
    ) -> MonthlyReport | None:
        return (
            db.query(MonthlyReport)
            .options(
                joinedload(MonthlyReport.student),
                selectinload(MonthlyReport.days),
            )
            .filter(
                MonthlyReport.student_id == student_id,
                MonthlyReport.year == year,
                MonthlyReport.month == month,
            )
            .first()
        )

    @staticmethod
    def list_for_student(db: Session, student_id: UUID) -> list[MonthlyReport]:
        return (
            db.query(MonthlyReport)
            .options(selectinload(MonthlyReport.days))
            .filter(MonthlyReport.student_id == student_id)
            .order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc())
            .all()
        )

    @staticmethod
    def list_reported_periods(db: Session) -> list[tuple[int, int]]:
        rows = db.query(MonthlyReport.year, MonthlyReport.month).distinct().all()
        return [(year, month) for year, month in rows]

    @staticmethod
    def list_for_period(db: Session, year: int, month: int):
        students = db.query(Student).order_by(Student.full_name.asc()).all()
        reports = (
            db.query(MonthlyReport)
            .options(selectinload(MonthlyReport.days))
            .filter(MonthlyReport.year == year, MonthlyReport.month == month)
            .all()
        )
        by_student = {}
        for report in reports:
            by_student.setdefault(report.student_id, []).append(report)
        return [
            (student, report)
            for student in students
            for report in (by_student.get(student.id) or [None])
        ]

    @staticmethod
    def count_for_student_period(db: Session, student_id, year: int, month: int) -> int:
        return (
            db.query(func.count(MonthlyReport.id))
            .filter(
                MonthlyReport.student_id == student_id,
                MonthlyReport.year == year,
                MonthlyReport.month == month,
            )
            .scalar()
        ) or 0

    @staticmethod
    def get_for_student_period_type(
        db: Session, student_id, year: int, month: int, report_type: ReportType
    ) -> MonthlyReport | None:
        return (
            db.query(MonthlyReport)
            .filter(
                MonthlyReport.student_id == student_id,
                MonthlyReport.year == year,
                MonthlyReport.month == month,
                MonthlyReport.report_type == report_type,
            )
            .first()
        )
    @staticmethod
    def search_period(
        db: Session,
        year: int,
        month: int,
        *,
        q: str | None = None,
        statuses: list[str] | None = None,
        report_types: list[str] | None = None,
        project_id=None,
        attention: str | None = None,
        sort: str = "name",
        order: str = "asc",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        day_stats = (
            select(
                DailyReport.monthly_report_id.label("report_id"),
                func.coalesce(func.sum(_DAY_MINUTES), 0).label("total_minutes"),
                func.coalesce(func.sum(_FILLED), 0).label("filled_days"),
                func.coalesce(func.sum(_ENTRY), 0).label("output_entries"),
            )
            .join(MonthlyReport, MonthlyReport.id == DailyReport.monthly_report_id)
            .where(MonthlyReport.year == year, MonthlyReport.month == month)
            .group_by(DailyReport.monthly_report_id)
            .subquery()
        )
        total_minutes = func.coalesce(day_stats.c.total_minutes, 0)
        filled_days = func.coalesce(day_stats.c.filled_days, 0)
        output_entries = func.coalesce(day_stats.c.output_entries, 0)
        day_count = calendar.monthrange(year, month)[1]
        denominator = case((_IS_OUTPUT, output_entries), else_=day_count)
        completion = case(
            (denominator > 0, cast(filled_days, Float) / denominator), else_=0
        )

        def joined(stmt):
            return (
                stmt.select_from(Student)
                .outerjoin(
                    MonthlyReport,
                    and_(
                        MonthlyReport.student_id == Student.id,
                        MonthlyReport.year == year,
                        MonthlyReport.month == month,
                    ),
                )
                .outerjoin(day_stats, day_stats.c.report_id == MonthlyReport.id)
            )

        conds = list(_student_scope())
        if q and q.strip():
            like = (
                "%"
                + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            conds.append(
                or_(
                    Student.full_name.ilike(like, escape="\\"),
                    Student.kana_name.ilike(like, escape="\\"),
                    Student.student_code.ilike(like, escape="\\"),
                    Student.email.ilike(like, escape="\\"),
                )
            )
        if project_id:
            conds.append(
                exists().where(
                    ProjectMember.student_id == Student.id,
                    ProjectMember.project_id == project_id,
                    ProjectMember.left_at.is_(None),
                )
            )
        if report_types:
            parts = []
            for value in report_types:
                if value == "none":
                    parts.append(MonthlyReport.id.is_(None))
                else:
                    parts.append(MonthlyReport.report_type == ReportType.parse(value))
            conds.append(or_(*parts))
        if attention == "submitted_stale":
            conds.append(
                and_(
                    MonthlyReport.status == ReportStatus.SUBMITTED,
                    MonthlyReport.submitted_at <= datetime.utcnow() - timedelta(days=3),
                )
            )
        elif attention == "rejected":
            conds.append(MonthlyReport.status == ReportStatus.REJECTED)

        # status filtri alohida: status_counts uni hisobga olmaydi
        status_cond = None
        if statuses:
            parts = []
            for value in statuses:
                if value == "not_created":
                    parts.append(MonthlyReport.id.is_(None))
                else:
                    parts.append(MonthlyReport.status == ReportStatus.parse(value))
            status_cond = or_(*parts)
        where_all = conds + ([status_cond] if status_cond is not None else [])

        sort_keys = {
            "name": Student.full_name,
            "total_hours": total_minutes,
            "status": MonthlyReport.status,
            "updated_at": MonthlyReport.updated_at,
            "submitted_at": MonthlyReport.submitted_at,
            "completion": completion,
        }
        key = sort_keys.get(sort, Student.full_name)
        ordered = key.desc() if order == "desc" else key.asc()
        order_by = []
        if sort in sort_keys and sort != "name":
            order_by.append(MonthlyReport.id.is_(None))  # reportsiz qatorlar oxirida
        order_by.append(ordered.nulls_last())
        order_by += [
            Student.full_name.asc(),
            Student.id.asc(),
            MonthlyReport.title.asc().nulls_last(),
            MonthlyReport.id.asc().nulls_last(),
        ]

        total = db.execute(joined(select(func.count())).where(*where_all)).scalar_one()
        total_students = db.execute(
            joined(select(func.count(func.distinct(Student.id)))).where(*where_all)
        ).scalar_one()

        label = case(
            (MonthlyReport.id.is_(None), "not_created"),
            else_=func.lower(cast(MonthlyReport.status, String)),
        )
        counted = db.execute(
            joined(select(label, func.count())).where(*conds).group_by(label)
        ).all()
        status_counts = {name: 0 for name in STATUS_NAMES}
        status_counts.update({name: count for name, count in counted})

        offset = (max(page, 1) - 1) * limit
        rows = db.execute(
            joined(
                select(
                    Student,
                    MonthlyReport,
                    total_minutes.label("total_minutes"),
                    filled_days.label("filled_days"),
                    output_entries.label("output_entries"),
                )
            )
            .where(*where_all)
            .order_by(*order_by)
            .limit(limit)
            .offset(offset)
        ).all()

        return {
            "rows": rows,
            "total": total,
            "total_students": total_students,
            "status_counts": status_counts,
            "day_count": day_count,
        }    
