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
from src.repository.work_report_repository import STATUS_NAMES, WorkReportRepository
from src.schemas.work_report import (
    MonthlyReportCreateIn,
    MonthlyReportUpdateIn,
    ReportReviewIn,
)
from src.services.student_service import StudentService

MAX_REPORTS_PER_MONTH = 2
MAX_DAY_MINUTES = 9 * 60  # bir kunlik maksimum ish vaqti (9 soat)


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
        # tungi smena: yarim tundan o'tadi (22:00 -> 02:00 = 240 daqiqa)
        return 24 * 60 - start_m + finish_m
    return finish_m - start_m


def _reject_bad_day(entry, output: bool) -> None:
    """Bir kunlik yozuv qoidalari: 00:00 da boshlanmaydi, 9 soatdan oshmaydi."""
    if entry.is_day_off:
        return
    if output:
        minutes = entry.work_minutes or 0
    else:
        if entry.start_time is not None and entry.start_time == time(0, 0):
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_START_MIDNIGHT",
                "00:00 da boshlangan smena keyingi kunga yoziladi, shuning uchun bunday vaqt qabul qilinmaydi",
            )
        minutes = duration_minutes(entry.start_time, entry.finish_time)
    if minutes > MAX_DAY_MINUTES:
        _error(
            status.HTTP_400_BAD_REQUEST,
            "REPORT_DAY_TOO_LONG",
            "Bir kunlik ish vaqti 9 soatdan oshmasligi kerak",
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


def day_has_output_data(day: DailyReport) -> bool:
    """Output (成果制) kunlari ixtiyoriy: faqat ma'lumot kiritilgan kunlar hisobga olinadi."""
    return bool(
        (day.work_minutes or 0) > 0
        or (day.count_1 or 0) > 0
        or (day.count_2 or 0) > 0
        or _blank(day.description)
    )


def report_progress(days, report_type, year: int, month: int) -> dict:
    """Hisobot to'ldirilish ko'rsatkichlari.

    hourly: oyning barcha kalendar kunlari talab qilinadi.
    output: ishbay — faqat ma'lumot kiritilgan kunlar hisobga olinadi.
    """
    calendar_days = len(month_dates(year, month))
    if _is_output(report_type):
        entries = [day for day in days if day_has_output_data(day)]
        return {
            "day_count": calendar_days,
            "entry_count": len(entries),
            "filled_days": sum(1 for day in entries if day_is_complete(day, report_type)),
        }
    return {
        "day_count": calendar_days,
        "entry_count": calendar_days,
        "filled_days": sum(1 for day in days if day_is_complete(day, report_type)),
    }


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
    progress = report_progress(days, rtype, report.year, report.month)
    status_value = ReportStatus.parse(report.status).value
    student = report.student
    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": rtype.value,
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
        "filled_days": progress["filled_days"],
        "day_count": progress["day_count"],
        "entry_count": progress["entry_count"],
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
    progress = report_progress(days, rtype, year, month)
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
        "filled_days": progress["filled_days"],
        "day_count": progress["day_count"],
        "entry_count": progress["entry_count"],
        "stipend_amount": report.stipend_amount,
    }


def serialize_own_summary(report: MonthlyReport) -> dict:
    rtype = ReportType.parse(report.report_type)
    days = list(report.days)
    status_value = ReportStatus.parse(report.status).value
    progress = report_progress(days, rtype, report.year, report.month)
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
        "filled_days": progress["filled_days"],
        "day_count": progress["day_count"],
        "entry_count": progress["entry_count"],
        "submitted_at": _iso(report.submitted_at),
        "reviewed_at": _iso(report.reviewed_at),
        "updated_at": _iso(report.updated_at),
    }

def serialize_search_item(
    student: Student,
    report: MonthlyReport | None,
    total_minutes: int,
    filled_days: int,
    output_entries: int,
    day_count: int,
) -> dict:
    """Admin ro'yxati qatori. Soat va kunlar SQL'da hisoblangan (Python'da emas)."""
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
            "entry_count": 0,
            "stipend_amount": None,
            "submitted_at": None,
            "reviewed_at": None,
            "updated_at": None,
            "can_open": False,
        }
    rtype = ReportType.parse(report.report_type)
    status_value = ReportStatus.parse(report.status).value
    return {
        "student_id": str(student.id),
        "title": report.title,
        "report_type": rtype.value,
        "student_name": student.full_name,
        "student_code": student.student_code,
        "email": student.email,
        "report_id": str(report.id),
        "status": status_value,
        "total_minutes": int(total_minutes or 0),
        "filled_days": int(filled_days or 0),
        "day_count": day_count,
        "entry_count": int(output_entries or 0) if rtype is ReportType.OUTPUT else day_count,
        "stipend_amount": report.stipend_amount,
        "submitted_at": _iso(report.submitted_at),
        "reviewed_at": _iso(report.reviewed_at),
        "updated_at": _iso(report.updated_at),
        # draft qatorni ochib bo'lmaydi (REPORT_DRAFT_HIDDEN), frontend "Ochish" ni yashiradi
        "can_open": status_value != ReportStatus.DRAFT.value,
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
        if WorkReportRepository.get_for_student_period_type(
            db, student.id, year, month, payload.report_type
        ):
            _error(
                status.HTTP_409_CONFLICT,
                "REPORT_TYPE_EXISTS",
                f"Bu oyda {payload.report_type.value} turidagi hisobot allaqachon mavjud",
            )
        is_output = payload.report_type is ReportType.OUTPUT
        report = MonthlyReport(
            student_id=student.id,
            title=payload.title,
            report_type=payload.report_type,
            # Default label saqlanmaydi: frontend uni joriy tilga tarjima qiladi.
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
        current_types = {
            r.report_type.value
            for r in reports
            if r.year == today.year and r.month == today.month
        }
        return {
            "current_year": today.year,
            "current_month": today.month,
            "can_add_current": current_count < MAX_REPORTS_PER_MONTH,
            "available_report_types": [
                report_type.value
                for report_type in ReportType
                if report_type.value not in current_types
            ],
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
            # None = o'zgartirilmaydi, bo'sh string = tozalash (frontend tarjimaga fallback qiladi).
            if payload.condition_1_label is not None:
                report.condition_1_label = _blank(payload.condition_1_label)
            if payload.condition_2_label is not None:
                report.condition_2_label = _blank(payload.condition_2_label)

        for entry in payload.days:
            _reject_bad_day(entry, output)

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



        days = {day.work_date: day for day in report.days}
        if rtype is ReportType.OUTPUT:
            # 成果制: ishbay bo'lgani uchun oyning barcha kunlari shart emas.
            # Faqat ma'lumot kiritilgan kunlar to'liq bo'lishi kerak.
            if not any(day_has_output_data(day) for day in report.days):
                _error(
                    status.HTTP_400_BAD_REQUEST,
                    "REPORT_INCOMPLETE",
                    "Kamida bitta kun uchun ish vaqti yoki natija kiritilishi kerak",
                )
            for day in report.days:
                if day_has_output_data(day) and not day_is_complete(day, rtype):
                    _error(
                        status.HTTP_400_BAD_REQUEST,
                        "REPORT_INCOMPLETE",
                        "Ma'lumot kiritilgan har bir kunda ish vaqti (daqiqa) bo'lishi kerak",
                    )
        else:
            for work_date in month_dates(report.year, report.month):
                day = days.get(work_date)
                if day is None or not day_is_complete(day, rtype):
                    _error(
                        status.HTTP_400_BAD_REQUEST,
                        "REPORT_INCOMPLETE",
                        "Oy ichidagi har bir kun dam olish yoki start, finish, memo va soat bilan to'ldirilishi kerak",
                    )

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
    def _check_filters(
        statuses: list[str], report_types: list[str], attention: str | None
    ) -> None:
        bad_status = [s for s in statuses if s not in STATUS_NAMES]
        bad_type = [t for t in report_types if t not in ("hourly", "output", "none")]
        if bad_status or bad_type:
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_FILTER_INVALID",
                "Noto'g'ri filter qiymati",
            )
        only_not_created = bool(statuses) and set(statuses) == {"not_created"}
        wants_report = any(t != "none" for t in report_types) or attention is not None
        only_none_type = bool(report_types) and set(report_types) == {"none"}
        wants_real_status = any(s != "not_created" for s in statuses) or attention is not None
        if (only_not_created and wants_report) or (only_none_type and wants_real_status):
            _error(
                status.HTTP_400_BAD_REQUEST,
                "REPORT_FILTER_CONFLICT",
                "Bu filtrlar birga ishlamaydi: natija har doim bo'sh bo'ladi",
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
        project_id: UUID | None = None,
        attention: str | None = None,
        sort: str = "name",
        order: str = "asc",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        statuses = statuses or []
        report_types = report_types or []
        WorkReportService._check_filters(statuses, report_types, attention)
        result = WorkReportRepository.search_period(
            db,
            year,
            month,
            q=q,
            statuses=statuses or None,
            report_types=report_types or None,
            project_id=project_id,
            attention=attention,
            sort=sort,
            order=order,
            page=page,
            limit=limit,
        )
        day_count = result["day_count"]
        items = [
            serialize_search_item(student, report, minutes, filled, entries, day_count)
            for student, report, minutes, filled, entries in result["rows"]
        ]
        total = result["total"]
        return {
            "year": year,
            "month": month,
            "periods": WorkReportService.available_periods(db),
            "items": items,
            "total": total,
            "total_students": result["total_students"],
            "page": page,
            "limit": limit,
            "total_pages": max(1, -(-total // limit)),
            "status_counts": result["status_counts"],
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
    def list_period_exports(
        db: Session,
        year: int,
        month: int,
        *,
        q: str | None = None,
        statuses: list[str] | None = None,
        report_types: list[str] | None = None,
        project_id: UUID | None = None,
        attention: str | None = None,
        sort: str = "name",
        order: str = "asc",
    ) -> list[dict]:
        """Filtrga mos hisobotlar. Draft hisobotlar eksportga kirmaydi."""
        statuses = statuses or []
        report_types = report_types or []
        WorkReportService._check_filters(statuses, report_types, attention)
        result = WorkReportRepository.search_period(
            db,
            year,
            month,
            q=q,
            statuses=statuses or None,
            report_types=report_types or None,
            project_id=project_id,
            attention=attention,
            sort=sort,
            order=order,
            page=1,
            limit=100000,
        )
        return [
            serialize_report(row[1])
            for row in result["rows"]
            if row[1] is not None
            and ReportStatus.parse(row[1].status) is not ReportStatus.DRAFT
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
