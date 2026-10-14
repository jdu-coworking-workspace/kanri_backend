import secrets
from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.models.student import SemesterEnum, SkillRank, Student, WorkStatus
from src.models.user import User, UserRole
from src.repository import user_repository
from src.repository.student_repository import StudentRepository
from src.schemas.student import (
    StudentCreateSchema,
    StudentUpdateSchema,
    StudentCopySchema,
)
from src.utils.security import get_password_hash


class StudentService:

    @staticmethod
    def get_own_profile(db: Session, user: User) -> Student:
        if UserRole.parse(user.role) is not UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sizda bu sahifaga kirish huquqi yo'q",
            )
        student = StudentRepository.get_by_user_id(db, user.id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "STUDENT_PROFILE_NOT_FOUND",
                    "message": "Talaba profili topilmadi",
                },
            )
        return student

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
        skill_rank: Optional[SkillRank] = None,
        work_status: Optional[WorkStatus] = None,
        semester: Optional[SemesterEnum] = None,
    ) -> Tuple[List[Student], int]:
        if page < 1:
            page = 1
        if limit < 1:
            limit = 10
        return StudentRepository.get_list(
            db, page, limit, q, skill_rank, work_status, semester
        )

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
    def _open_student_login(db: Session, email: str, full_name: str) -> tuple[User, str]:
        if user_repository.get_user_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu email allaqachon foydalanuvchi sifatida mavjud",
            )
        plain_password = secrets.token_urlsafe(12)
        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.STUDENT,
            password_hash=get_password_hash(plain_password),
        )
        db.add(user)
        db.flush()
        return user, plain_password

    @staticmethod
    def _notify_password(plain_password: str) -> None:
        # SES keyinroq ulanadi. Hozircha parol logga chiqadi.
        print("email jonatilindi", plain_password)

    @staticmethod
    def create_student(db: Session, student_data: StudentCreateSchema) -> Student:
        StudentService._ensure_unique(db, student_data.student_code, student_data.email)
        user, plain_password = StudentService._open_student_login(
            db, student_data.email, student_data.full_name
        )
        payload = student_data.model_dump()
        payload["user_id"] = user.id
        student = StudentRepository.create(db, payload)
        StudentService._notify_password(plain_password)
        return student

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

        if "email" in update_data and student.user_id:
            new_email = update_data["email"]
            existing_user = user_repository.get_user_by_email(db, new_email)
            if existing_user is not None and str(existing_user.id) != str(student.user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu email allaqachon foydalanuvchi sifatida mavjud",
                )
            login_user = user_repository.get_user_by_id(db, student.user_id)
            if login_user is not None:
                login_user.email = new_email

        return StudentRepository.update(db, student, update_data)

    @staticmethod
    def delete_student(db: Session, student_id: UUID) -> None:
        student = StudentService.get_student(db, student_id)
        login_user_id = student.user_id
        StudentRepository.delete(db, student)
        if login_user_id:
            login_user = user_repository.get_user_by_id(db, login_user_id)
            if login_user is not None:
                user_repository.delete_user(db, login_user)

    @staticmethod
    def get_student_with_history(db: Session, student_id: UUID):
        student = StudentService.get_student(db, student_id)
        memberships = StudentRepository.get_memberships(db, student_id)
        return student, memberships

    @staticmethod
    def copy_student(
        db: Session,
        student_id: UUID,
        copy_data: StudentCopySchema,
    ) -> Student:
        source = StudentService.get_student(db, student_id)

        StudentService._ensure_unique(db, copy_data.student_code, copy_data.email)
        full_name = copy_data.full_name or source.full_name
        user, plain_password = StudentService._open_student_login(
            db, copy_data.email, full_name
        )

        new_data = {
            "full_name": full_name,
            "kana_name": copy_data.kana_name or source.kana_name,
            "student_code": copy_data.student_code,
            "email": copy_data.email,
            "avatar_url": None,  # nusxada yangi avatar alohida yuklanadi
            "grad_year_month": source.grad_year_month,
            "semester": source.semester,
            "skill_rank": source.skill_rank,
            "work_status": source.work_status,
            "user_id": user.id,
        }

        student = StudentRepository.create(db, new_data)
        StudentService._notify_password(plain_password)
        return student
