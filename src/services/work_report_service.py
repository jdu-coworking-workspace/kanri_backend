import calendar
from datetime import date, datetime, time
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.student import Student
from src.models.user import User
from src.models.work_report import DailyReport, MonthlyReport, ReportStatus, ReportType
from src.repository.work_report_repository import WorkReportRepository
from src.schemas.work_report import (
    MonthlyReportCreateIn,
    MonthlyReportUpdateIn,
    ReportReviewIn,
)
from src.services.student_service import StudentService

MAX_REPORTS_PER_MONTH = 2


def _error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def month_dates(year: int, month: int) -> list[date]:
    _, last_day = calendar.monthrange(year, month)
    return [date(year, month, day) for day in range(1, last_day + 1)]


def assert_not_future(year: int, month: int) -> None:
    today = date.today()
    if (year, month) > (today.year, today.month):
        _error(
            status.HTTP_400_BAD_REQUEST, "REPORT_FUTURE_MONTH", "Kelajak oyi ochilmaydi"
        )


def duration_minutes(
    start: time | None, finish: time | None, is_day_off: bool = False
) -> int:
    if is_day_off or start is None or finish is None:
        return 0
    start_m = start.hour * 60 + start.minute
    finish_m = finish.hour * 60 + finish.minute
    if finish_m < start_m:
        return 0
    return finish_m - start_m


def _reject_time_order(start: time | None, finish: time | None) -> None:
    if start is not None and finish is not None and start > finish:
        _error(
            status.HTTP_400_BAD_REQUEST,
            "REPORT_TIME_ORDER",
            "Boshlanish vaqti tugash vaqtidan katta bo'lmasligi kerak",
        )


def _time_str(value: time | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%H:%M")


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _is_output(report_type) -> bool:
    return ReportType.parse(report_type) is ReportType.OUTPUT


def day_minutes(day: DailyReport, report_type) -> int:
    if day.is_day_off:
        return 0
    if _is_output(report_type):
        return day.work_minutes or 0
    return duration_minutes(day.start_time, day.finish_time)


def day_is_complete(day: DailyReport, report_type) -> bool:
    if day.is_day_off:
        return True
    if _is_output(report_type):
        return (day.work_minutes or 0) > 0
    if not (day.start_time and day.finish_time and _blank(day.description)):
        return False
    return duration_minutes(day.start_time, day.finish_time) > 0


def serialize_day(day: DailyReport, report_type) -> dict:
    output = _is_output(report_type)
    overnight = False
    if not output and day.start_time and day.finish_time and not day.is_day_off:
        start_m = day.start_time.hour * 60 + day.start_time.minute
        finish_m = day.finish_time.hour * 60 + day.finish_time.minute
        overnight = finish_m < start_m
    return {
        "id": str(day.id),
        "work_date": day.work_date.isoformat(),
        "start_time": _time_str(day.start_time),
        "finish_time": _time_str(day.finish_time),
        "description": day.description,
        "is_day_off": bool(day.is_day_off),
        "duration_minutes": day_minutes(day, report_type),
        "overnight": overnight,
        "work_minutes": day.work_minutes,
        "count_1": day.count_1,
        "count_2": day.count_2,
        "is_approved": day.is_approved,
        "approved_count_1": day.approved_count_1,
        "approved_count_2": day.approved_count_2,
    }


def serialize_report(report: MonthlyReport) -> dict:
    days = sorted(report.days, key=lambda item: item.work_date)
    rtype = ReportType.parse(report.report_type)
    day_rows = [serialize_day(day, rtype) for day in days]
    total = sum(row["duration_minutes"] for row in day_rows)
    status_value = ReportStatus.parse(report.status).value
    student = report.student
    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": rtype.value,
        "cowork_no": report.cowork_no,
        "condition_1_label": report.condition_1_label,
        "condition_2_label": report.condition_2_label,
        "unit_price_1": report.unit_price_1,
        "unit_price_2": report.unit_price_2,
        "student_id": str(report.student_id),
        "student_name": student.full_name if student else None,
        "student_code": student.student_code if student else None,
        "email": student.email if student else None,
        "year": report.year,
        "month": report.month,
        "status": status_value,
        "editable": status_value
        in (ReportStatus.DRAFT.value, ReportStatus.REJECTED.value),
        "week_1": report.week_1,
        "week_2": report.week_2,
        "week_3": report.week_3,
        "week_4": report.week_4,
        "week_5": report.week_5,
        "stipend_amount": report.stipend_amount,
        "review_note": report.review_note,
        "submitted_at": _iso(report.submitted_at),
        "reviewed_at": _iso(report.reviewed_at),
        "updated_at": _iso(report.updated_at),
        "total_minutes": total,
        "total_count_1": sum(d.count_1 or 0 for d in days),
        "total_count_2": sum(d.count_2 or 0 for d in days),
        "filled_days": sum(1 for day in days if day_is_complete(day, rtype)),
        "day_count": len(month_dates(report.year, report.month)),
        "days": day_rows,
    }


def serialize_list_item(
    student: Student, report: MonthlyReport | None, year: int, month: int
) -> dict:
    day_count = len(month_dates(year, month))
    if report is None:
        return {
            "student_id": str(student.id),
            "title": None,
            "report_type": None,
            "student_name": student.full_name,
            "student_code": student.student_code,
            "email": student.email,
            "report_id": None,
            "status": None,
            "total_minutes": 0,
            "filled_days": 0,
            "day_count": day_count,
            "stipend_amount": None,
        }
    rtype = ReportType.parse(report.report_type)
    days = list(report.days)
    total = sum(day_minutes(day, rtype) for day in days)
    return {
        "student_id": str(student.id),
        "title": report.title,
        "report_type": rtype.value,
        "student_name": student.full_name,
        "student_code": student.student_code,
        "email": student.email,
        "report_id": str(report.id),
        "status": ReportStatus.parse(report.status).value,
        "total_minutes": total,
        "filled_days": sum(1 for day in days if day_is_complete(day, rtype)),
        "day_count": day_count,
        "stipend_amount": report.stipend_amount,
    }


def serialize_own_summary(report: MonthlyReport) -> dict:
    rtype = ReportType.parse(report.report_type)
    days = list(report.days)
    status_value = ReportStatus.parse(report.status).value
    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": rtype.value,
        "year": report.year,
        "month": report.month,
        "status": status_value,
        "editable": status_value
        in (ReportStatus.DRAFT.value, ReportStatus.REJECTED.value),
        "review_note": report.review_note,
        "stipend_amount": report.stipend_amount,
        "total_minutes": sum(day_minutes(day, rtype) for day in days),
        "filled_days": sum(1 for day in days if day_is_complete(day, rtype)),
        "day_count": len(month_dates(report.year, report.month)),
        "submitted_at": _iso(report.submitted_at),
        "reviewed_at": _iso(report.reviewed_at),
        "updated_at": _iso(report.updated_at),
    }


def notify_report_decision(
    email: str, year: int, month: int, decision: str, note: str | None
) -> None:
    """SES ulanmaguncha xat terminalga yoziladi."""
    print("email jonatilindi", email, f"{year}-{month:02d}", decision, note or "")


class WorkReportService:

    @staticmethod
    def _load(db: Session, report_id: UUID) -> MonthlyReport:
        report = WorkReportRepository.get_by_id(db, report_id)
        if not report:
            _error(status.HTTP_404_NOT_FOUND, "REPORT_NOT_FOUND", "Hisobot topilmadi")
        return report

    @staticmethod
    def _create(
        db: Session,
        student: Student,
        year: int,
        month: int,
        payload: MonthlyReportCreateIn,
    ) -> MonthlyReport:
        assert_not_future(year, month)
        count = WorkReportRepository.count_for_student_period(
            db, student.id, year, month
        )
        if count >= MAX_REPORTS_PER_MONTH:
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_LIMIT_REACHED",
                f"Bir oyda ko'pi bilan {MAX_REPORTS_PER_MONTH} ta hisobot yaratish mumkin",
            )
        is_output = payload.report_type is ReportType.OUTPUT
        report = MonthlyReport(
            student_id=student.id,
            title=payload.title,
            report_type=payload.report_type,
            cowork_no=_blank(payload.cowork_no) if is_output else None,
            condition_1_label=_blank(payload.condition_1_label) if is_output else None,
            condition_2_label=_blank(payload.condition_2_label) if is_output else None,
            year=year,
            month=month,
            status=ReportStatus.DRAFT,
        )
        try:
            with db.begin_nested():
                db.add(report)
                db.flush()
                for work_date in month_dates(year, month):
                    db.add(
                        DailyReport(
                            monthly_report_id=report.id,
                            work_date=work_date,
                            is_day_off=False,
                        )
                    )
                db.flush()
        except IntegrityError:
            _error(
                status.HTTP_409_CONFLICT,
                "REPORT_TITLE_EXISTS",
                "Bu oyda shu nomli hisobot allaqachon mavjud",
            )

        db.commit()
        loaded = WorkReportRepository.get_by_id(db, report.id)
        if not loaded:
            _error(status.HTTP_404_NOT_FOUND, "REPORT_NOT_FOUND", "Hisobot topilmadi")
        return loaded

    @staticmethod
    def _own(db: Session, user: User, report_id: UUID) -> MonthlyReport:
        student = StudentService.get_own_profile(db, user)
        report = WorkReportRepository.get_by_id(db, report_id)
        if not report or report.student_id != student.id:
            _error(status.HTTP_404_NOT_FOUND, "REPORT_NOT_FOUND", "Hisobot topilmadi")
        return report

    @staticmethod
    def list_own(db: Session, user: User) -> dict:
        student = StudentService.get_own_profile(db, user)
        today = date.today()
        reports = WorkReportRepository.list_for_student(db, student.id)
        current_count = sum(
            1 for r in reports if r.year == today.year and r.month == today.month
        )
        return {
            "current_year": today.year,
            "current_month": today.month,
            "can_add_current": current_count < MAX_REPORTS_PER_MONTH,
            "items": [serialize_own_summary(report) for report in reports],
        }

    @staticmethod
    def create_own(db: Session, user: User, payload: MonthlyReportCreateIn) -> dict:
        student = StudentService.get_own_profile(db, user)
        today = date.today()
        return serialize_report(
            WorkReportService._create(db, student, today.year, today.month, payload)
        )

    @staticmethod
    def get_own_by_id(db: Session, user: User, report_id: UUID) -> dict:
        return serialize_report(WorkReportService._own(db, user, report_id))

    @staticmethod
    def update_own(
        db: Session, user: User, report_id: UUID, payload: MonthlyReportUpdateIn
    ) -> dict:
        report = WorkReportService._own(db, user, report_id)
        WorkReportService._ensure_editable(report)
        output = _is_output(report.report_type)

        if payload.year != report.year or payload.month != report.month:
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_DATE_OUT_OF_MONTH",
                "Sana shu oyga tegishli emas",
            )

        if _blank(payload.title):
            report.title = _blank(payload.title)
        if output:
            if payload.cowork_no is not None:
                report.cowork_no = _blank(payload.cowork_no)
            if _blank(payload.condition_1_label):
                report.condition_1_label = _blank(payload.condition_1_label)
            if payload.condition_2_label is not None:
                report.condition_2_label = _blank(payload.condition_2_label)
        else:
            for entry in payload.days:
                if not entry.is_day_off:
                    _reject_time_order(entry.start_time, entry.finish_time)

        expected = set(month_dates(payload.year, payload.month))
        seen = set()
        by_date = {day.work_date: day for day in report.days}
        for entry in payload.days:
            if entry.work_date not in expected:
                _error(
                    status.HTTP_400_BAD_REQUEST,
                    "REPORT_DATE_OUT_OF_MONTH",
                    "Sana shu oyga tegishli emas",
                )
            if entry.work_date in seen:
                _error(
                    status.HTTP_400_BAD_REQUEST,
                    "REPORT_DUPLICATE_DATE",
                    "Sana takrorlangan",
                )
            seen.add(entry.work_date)
            row = by_date.get(entry.work_date)
            if row is None:
                row = DailyReport(
                    monthly_report_id=report.id, work_date=entry.work_date
                )
                db.add(row)
                report.days.append(row)
                by_date[entry.work_date] = row

            row.is_day_off = entry.is_day_off
            if entry.is_day_off:
                row.start_time = None
                row.finish_time = None
                row.description = None
                row.work_minutes = None
                row.count_1 = None
                row.count_2 = None
            elif output:
                row.start_time = None
                row.finish_time = None
                row.work_minutes = entry.work_minutes
                row.count_1 = entry.count_1
                row.count_2 = entry.count_2
                row.description = _blank(entry.description)
            else:
                row.start_time = entry.start_time
                row.finish_time = entry.finish_time
                row.description = _blank(entry.description)
                row.work_minutes = None
                row.count_1 = None
                row.count_2 = None

        for index in range(1, 6):
            setattr(report, f"week_{index}", _blank(getattr(payload, f"week_{index}")))

        report.updated_at = datetime.utcnow()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            _error(
                status.HTTP_409_CONFLICT,
                "REPORT_TITLE_EXISTS",
                "Bu oyda shu nomli hisobot allaqachon mavjud",
            )
        return serialize_report(WorkReportService._load(db, report.id))

    @staticmethod
    def submit_own(db: Session, user: User, report_id: UUID) -> dict:
        report = WorkReportService._own(db, user, report_id)
        WorkReportService._ensure_editable(report)
        rtype = ReportType.parse(report.report_type)

        if rtype is ReportType.HOURLY:
            for day in report.days:
                _reject_time_order(day.start_time, day.finish_time)

        days = {day.work_date: day for day in report.days}
        for work_date in month_dates(report.year, report.month):
            day = days.get(work_date)
            if day is None or not day_is_complete(day, rtype):
                message = (
                    "Oy ichidagi har bir kun dam olish yoki ish vaqti bilan to'ldirilishi kerak"
                    if rtype is ReportType.OUTPUT
                    else "Oy ichidagi har bir kun dam olish yoki start, finish, memo va soat bilan to'ldirilishi kerak"
                )
                _error(status.HTTP_400_BAD_REQUEST, "REPORT_INCOMPLETE", message)

        report.status = ReportStatus.SUBMITTED
        report.submitted_at = datetime.utcnow()
        report.review_note = None
        report.reviewed_at = None
        report.reviewed_by = None
        report.updated_at = datetime.utcnow()
        db.commit()
        return serialize_report(WorkReportService._load(db, report.id))

    @staticmethod
    def available_periods(db: Session) -> list[dict]:
        today = date.today()
        periods = {
            (year, month)
            for year, month in WorkReportRepository.list_reported_periods(db)
            if (year, month) <= (today.year, today.month)
        }
        periods.add((today.year, today.month))
        ordered = sorted(periods, reverse=True)
        return [{"year": year, "month": month} for year, month in ordered]

    @staticmethod
    def list_period(db: Session, year: int, month: int) -> dict:
        rows = WorkReportRepository.list_for_period(db, year, month)
        return {
            "year": year,
            "month": month,
            "periods": WorkReportService.available_periods(db),
            "items": [
                serialize_list_item(student, report, year, month)
                for student, report in rows
            ],
        }

    @staticmethod
    def get_detail(db: Session, report_id: UUID) -> dict:
        report = WorkReportService._load(db, report_id)
        if ReportStatus.parse(report.status) == ReportStatus.DRAFT:
            _error(
                status.HTTP_403_FORBIDDEN,
                "REPORT_DRAFT_HIDDEN",
                "Qoralama hisobotni ochib bo'lmaydi",
            )
        return serialize_report(report)

    @staticmethod
    def get_export_detail(db: Session, report_id: UUID) -> dict:
        """Full report for Excel export. Unlike get_detail this also returns
        drafts, so an admin can download a month that is still in progress."""
        return serialize_report(WorkReportService._load(db, report_id))

    @staticmethod
    def list_period_exports(db: Session, year: int, month: int) -> list[dict]:
        """Every existing report of one period, drafts included, ready for export."""
        rows = WorkReportRepository.list_for_period(db, year, month)
        return [
            serialize_report(report) for _student, report in rows if report is not None
        ]

    @staticmethod
    def accept(
        db: Session, report_id: UUID, reviewer: User, payload: ReportReviewIn
    ) -> dict:
        return WorkReportService._decide(
            db, report_id, reviewer, payload, ReportStatus.APPROVED, "accepted"
        )

    @staticmethod
    def reject(
        db: Session, report_id: UUID, reviewer: User, payload: ReportReviewIn
    ) -> dict:
        return WorkReportService._decide(
            db, report_id, reviewer, payload, ReportStatus.REJECTED, "rejected"
        )

    @staticmethod
    def _decide(
        db: Session,
        report_id: UUID,
        reviewer: User,
        payload: ReportReviewIn,
        next_status: ReportStatus,
        decision: str,
    ) -> dict:
        report = WorkReportService._load(db, report_id)
        if ReportStatus.parse(report.status) is not ReportStatus.SUBMITTED:
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_NOT_SUBMITTED",
                "Faqat yuborilgan hisobotni baholash mumkin",
            )
        report.status = next_status
        report.review_note = _blank(payload.review_note)
        report.reviewed_at = datetime.utcnow()
        report.reviewed_by = reviewer.id
        if next_status is ReportStatus.APPROVED:
            report.stipend_amount = payload.stipend_amount
        db.commit()
        loaded = WorkReportService._load(db, report.id)
        email = loaded.student.email if loaded.student else None
        if email:
            notify_report_decision(
                email, loaded.year, loaded.month, decision, loaded.review_note
            )
        return serialize_report(loaded)

    @staticmethod
    def _ensure_editable(report: MonthlyReport) -> None:
        if ReportStatus.parse(report.status) not in (
            ReportStatus.DRAFT,
            ReportStatus.REJECTED,
        ):
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_LOCKED",
                "Yuborilgan hisobotni tahrirlash mumkin emas",
            )
