from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.models.student import Student
from src.repository.student_repository import StudentRepository
from src.schemas.student import (
    StudentCreateSchema,
    StudentUpdateSchema,
    StudentCopySchema,
)


class StudentService:

    @staticmethod
    def get_student(db: Session, student_id: UUID) -> Student:
        student = StudentRepository.get_by_id(db, student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Talaba topilmadi",
            )
        return student

    @staticmethod
    def get_students(
        db: Session,
        page: int,
        limit: int,
        q: Optional[str] = None,
    ) -> Tuple[List[Student], int]:
        if page < 1:
            page = 1
        if limit < 1:
            limit = 10
        return StudentRepository.get_list(db, page, limit, q)

    @staticmethod
    def _ensure_unique(
        db: Session,
        student_code: str,
        email: str,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        existing_by_code = StudentRepository.get_by_student_code(db, student_code)
        if existing_by_code is not None and str(existing_by_code.id) != str(exclude_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu student_code allaqachon mavjud",
            )

        existing_by_email = StudentRepository.get_by_email(db, email)
        if existing_by_email is not None and str(existing_by_email.id) != str(
            exclude_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu email allaqachon mavjud",
            )

    @staticmethod
    def create_student(db: Session, student_data: StudentCreateSchema) -> Student:
        StudentService._ensure_unique(db, student_data.student_code, student_data.email)
        return StudentRepository.create(db, student_data.model_dump())

    @staticmethod
    def update_student(
        db: Session,
        student_id: UUID,
        student_data: StudentUpdateSchema,
    ) -> Student:
        student = StudentService.get_student(db, student_id)
        update_data = student_data.model_dump(exclude_unset=True)

        if "student_code" in update_data or "email" in update_data:
            StudentService._ensure_unique(
                db,
                student_code=update_data.get("student_code", student.student_code),
                email=update_data.get("email", student.email),
                exclude_id=UUID(str(student.id)),
            )

        return StudentRepository.update(db, student, update_data)

    @staticmethod
    def delete_student(db: Session, student_id: UUID) -> None:
        student = StudentService.get_student(db, student_id)
        StudentRepository.delete(db, student)

    @staticmethod
    def copy_student(
        db: Session,
        student_id: UUID,
        copy_data: StudentCopySchema,
    ) -> Student:
        source = StudentService.get_student(db, student_id)

        StudentService._ensure_unique(db, copy_data.student_code, copy_data.email)

        new_data = {
            "full_name": copy_data.full_name or source.full_name,
            "kana_name": copy_data.kana_name or source.kana_name,
            "student_code": copy_data.student_code,
            "email": copy_data.email,
            "avatar_url": source.avatar_url,
            "grad_year_month": source.grad_year_month,
            "semester": source.semester,
            "skill_rank": source.skill_rank,
            "work_status": source.work_status,
            "point_1": source.point_1,
            "point_2": source.point_2,
            "point_3": source.point_3,
        }

        return StudentRepository.create(db, new_data)
