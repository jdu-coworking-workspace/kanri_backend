from typing import Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.deps import (
    get_current_user,
    require_editor,
)  # NOTE: yo'lni loyihangizga qarab moslang
from src.models.user import User
from src.schemas.student import (
    StudentCreateSchema,
    StudentUpdateSchema,
    StudentOutSchema,
    StudentCopySchema,
    StudentListSchema,
)
from src.services.student_service import StudentService

router = APIRouter()


@router.get("", response_model=StudentListSchema)
def get_students(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    limit: int = Query(10, ge=1, le=100, description="Sahifadagi elementlar soni"),
    q: Optional[str] = Query(
        None, description="full_name, kana_name yoki student_code bo'yicha qidiruv"
    ),
    db: Session = Depends(get_db),
):
    items, total = StudentService.get_students(db, page, limit, q)
    return StudentListSchema(
        items=[StudentOutSchema.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{student_id}", response_model=StudentOutSchema)
def get_student(
    student_id: UUID,
    db: Session = Depends(get_db),
):
    return StudentService.get_student(db, student_id)


@router.post("", response_model=StudentOutSchema, status_code=status.HTTP_201_CREATED)
def create_student(
    student_data: StudentCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    return StudentService.create_student(db, student_data)


@router.put("/{student_id}", response_model=StudentOutSchema)
def update_student(
    student_id: UUID,
    student_data: StudentUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    return StudentService.update_student(db, student_id, student_data)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    StudentService.delete_student(db, student_id)


@router.post(
    "/{student_id}/copy",
    response_model=StudentOutSchema,
    status_code=status.HTTP_201_CREATED,
)
def copy_student(
    student_id: UUID,
    copy_data: StudentCopySchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    return StudentService.copy_student(db, student_id, copy_data)
