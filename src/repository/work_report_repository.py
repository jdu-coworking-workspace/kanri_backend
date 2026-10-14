from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload, selectinload

from src.models.student import Student
from src.models.work_report import MonthlyReport


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
        by_student = {report.student_id: report for report in reports}
        return [(student, by_student.get(student.id)) for student in students]
