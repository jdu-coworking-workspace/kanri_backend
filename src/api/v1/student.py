from math import ceil
from typing import Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.deps import get_current_user, require_admin
from src.models.user import User
from src.schemas.student import (
    StudentCreateSchema,
    StudentUpdateSchema,
    StudentOutSchema,
    StudentDetailSchema,
    StudentHistoryItemSchema,
    StudentCopySchema,
)
from src.services.student_service import StudentService

router = APIRouter()


def _build_history(memberships) -> list:
    """ProjectMember ro'yxatini StudentHistoryItemSchema ro'yxatiga aylantiradi."""
    return [
        StudentHistoryItemSchema(
            project_id=pm.project_id,
            project_name=pm.project.name,
            joined_at=pm.joined_at,
            left_at=pm.left_at,
            is_leader=pm.is_leader or False,
        )
        for pm in memberships
    ]


# ─── GET /students ────────────────────────────────────────────────────────────
@router.get("")
def get_students(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    limit: int = Query(10, ge=1, le=100, description="Sahifadagi elementlar soni"),
    q: Optional[str] = Query(
        None, description="full_name, kana_name yoki student_code bo'yicha qidiruv"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = StudentService.get_students(db, page, limit, q)
    total_pages = ceil(total / limit) if total > 0 else 1
    return {
        "success": True,
        "data": [StudentOutSchema.model_validate(item) for item in items],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        },
    }


# ─── GET /students/{student_id}/history ───────────────────────────────────────
# NOTE: Bu route /{student_id} dan OLDIN joylashtirilishi shart emas (ikki segment
# vs bir segment), lekin o'qish qulayligi uchun oldin yozildi.
@router.get("/{student_id}/history")
def get_student_history(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student, memberships = StudentService.get_student_with_history(db, student_id)
    return {
        "success": True,
        "data": _build_history(memberships),
    }


# ─── GET /students/{student_id} ───────────────────────────────────────────────
@router.get("/{student_id}")
def get_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student, memberships = StudentService.get_student_with_history(db, student_id)
    history = _build_history(memberships)
    student_out = StudentOutSchema.model_validate(student)
    detail = StudentDetailSchema(**student_out.model_dump(), history=history)
    return {"success": True, "data": detail}


# ─── POST /students ───────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_student(
    student_data: StudentCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = StudentService.create_student(db, student_data)
    return {"success": True, "data": StudentOutSchema.model_validate(student)}


# ─── PUT /students/{student_id} ───────────────────────────────────────────────
@router.put("/{student_id}")
def update_student(
    student_id: UUID,
    student_data: StudentUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = StudentService.update_student(db, student_id, student_data)
    return {"success": True, "data": StudentOutSchema.model_validate(student)}


# ─── DELETE /students/{student_id} ────────────────────────────────────────────
@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    StudentService.delete_student(db, student_id)


# ─── POST /students/{student_id}/copy ─────────────────────────────────────────
@router.post("/{student_id}/copy", status_code=status.HTTP_201_CREATED)
def copy_student(
    student_id: UUID,
    copy_data: StudentCopySchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = StudentService.copy_student(db, student_id, copy_data)
    return {"success": True, "data": StudentOutSchema.model_validate(student)}
