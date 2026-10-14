from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query, status
# pyrefly: ignore [missing-import]
from fastapi.responses import Response

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_admin, require_staff_or_admin
from src.database.session import get_db
from src.models.user import User
from src.schemas.work_report import MonthlyReportUpdateIn, ReportReviewIn
from src.services.work_report_service import WorkReportService
from src.utils.report_excel import build_monthly_report_xlsx
from src.utils.report_excel_batch import build_period_archive

router = APIRouter()


@router.get("/me")
def list_own_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "data": WorkReportService.list_own(db, current_user)}


@router.post("/me")
def create_own_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "data": WorkReportService.create_current(db, current_user)}


@router.get("/me/{report_id}")
def get_own_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "data": WorkReportService.get_own_by_id(db, current_user, report_id)}


@router.put("/me/{report_id}")
def update_own_report(
    report_id: UUID,
    payload: MonthlyReportUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": WorkReportService.update_own(db, current_user, report_id, payload),
    }


@router.post("/me/{report_id}/submit")
def submit_own_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "data": WorkReportService.submit_own(db, current_user, report_id)}


@router.get("")
def list_reports(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
):
    return {"success": True, "data": WorkReportService.list_period(db, year, month)}


# Declared before "/{report_id}" so the literal path wins over the UUID route.
@router.get("/export")
def export_period(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    reports = WorkReportService.list_period_exports(db, year, month)
    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_EXPORT_EMPTY", "message": "Bu oy uchun hisobot topilmadi"},
        )
    content = build_period_archive(reports, year, month)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="reports_{year}-{month:02d}.zip"'},
    )


@router.get("/{report_id}")
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
):
    return {"success": True, "data": WorkReportService.get_detail(db, report_id)}


@router.post("/{report_id}/accept")
def accept_report(
    report_id: UUID,
    payload: ReportReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return {
        "success": True,
        "data": WorkReportService.accept(db, report_id, current_user, payload),
    }


@router.post("/{report_id}/reject")
def reject_report(
    report_id: UUID,
    payload: ReportReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return {
        "success": True,
        "data": WorkReportService.reject(db, report_id, current_user, payload),
    }


@router.get("/{report_id}/export")
def export_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    report = WorkReportService.get_export_detail(db, report_id)
    content = build_monthly_report_xlsx(report)
    filename = f"{report['student_code']}_{report['year']}-{report['month']:02d}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
