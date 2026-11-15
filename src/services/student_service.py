import secrets
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from pydantic import ValidationError

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
from src.utils.s3 import get_anonymous_avatar_url
from src.utils.student_import import parse_student_file

ANONYMOUS_AVATAR_URL = get_anonymous_avatar_url()

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
    def _open_student_login(
        db: Session, email: str, full_name: str
    ) -> tuple[User, str]:
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
        if not payload.get("avatar_url"):
            payload["avatar_url"] = ANONYMOUS_AVATAR_URL
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
            if existing_user is not None and str(existing_user.id) != str(
                student.user_id
            ):
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
            "avatar_url": ANONYMOUS_AVATAR_URL,  # nusxada yangi avatar alohida yuklanadi
            "grad_year_month": source.grad_year_month,
            "semester": source.semester,
            "skill_rank": source.skill_rank,
            "work_status": source.work_status,
            "user_id": user.id,
        }

        student = StudentRepository.create(db, new_data)
        StudentService._notify_password(plain_password)
        return student

    @staticmethod
    def bulk_create_from_file(
        db: Session,
        filename: str,
        content: bytes,
        skip_invalid: bool = False,
    ) -> dict:
        """Yuklangan .xlsx/.csv faylni parse qilib, bulk yaratishni bajaradi."""
        rows = parse_student_file(filename, content)
        return StudentService.bulk_create_students(db, rows, skip_invalid)

    @staticmethod
    def _clean_row(raw: Any) -> Dict[str, Any]:
        """Excel'dan kelgan bo'sh katak ("" yoki bo'sh joy) -> None, matnlarni strip qiladi."""
        if not isinstance(raw, dict):
            return {}
        cleaned: Dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    value = None
            cleaned[key] = value
        return cleaned

    @staticmethod
    def bulk_create_students(
        db: Session,
        rows: List[Dict[str, Any]],
        skip_invalid: bool = False,
    ) -> dict:
        errors: List[dict] = []
        valid: List[Tuple[int, StudentCreateSchema]] = []

        def add_error(
            row_no: int, cleaned: Dict[str, Any], messages: List[str]
        ) -> None:
            errors.append(
                {
                    "row": row_no,
                    "student_code": cleaned.get("student_code"),
                    "email": cleaned.get("email"),
                    "errors": messages,
                }
            )

        # 1-bosqich: har bir qatorni alohida validatsiya qilish
        for idx, raw in enumerate(rows, start=1):
            cleaned = StudentService._clean_row(raw)
            row_no = idx
            if isinstance(raw, dict) and isinstance(raw.get("row"), int):
                row_no = raw["row"]
            try:
                data = StudentCreateSchema.model_validate(cleaned)
            except ValidationError as exc:
                messages = [
                    f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                    for err in exc.errors()
                ]
                add_error(row_no, cleaned, messages)
                continue
            valid.append((row_no, data))

        # 2-bosqich: fayl ichidagi dublikatlar (birinchi uchragani qoladi)
        seen_codes: Dict[str, int] = {}
        seen_emails: Dict[str, int] = {}
        unique_rows: List[Tuple[int, StudentCreateSchema]] = []
        for row_no, data in valid:
            msgs: List[str] = []
            code_key = data.student_code
            email_key = data.email.lower()
            if code_key in seen_codes:
                msgs.append(
                    f"student_code faylda takrorlangan ({seen_codes[code_key]}-qator bilan)"
                )
            if email_key in seen_emails:
                msgs.append(
                    f"email faylda takrorlangan ({seen_emails[email_key]}-qator bilan)"
                )
            if msgs:
                add_error(row_no, data.model_dump(), msgs)
                continue
            seen_codes[code_key] = row_no
            seen_emails[email_key] = row_no
            unique_rows.append((row_no, data))

        # 3-bosqich: bazadagi dublikatlar (bitta-bitta emas, IN bilan)
        existing_codes = StudentRepository.get_existing_student_codes(
            db, [d.student_code for _, d in unique_rows]
        )
        emails_lower = [d.email.lower() for _, d in unique_rows]
        existing_student_emails = StudentRepository.get_existing_student_emails(
            db, emails_lower
        )
        existing_user_emails = StudentRepository.get_existing_user_emails(
            db, emails_lower
        )

        to_create: List[Tuple[int, StudentCreateSchema]] = []
        for row_no, data in unique_rows:
            msgs = []
            if data.student_code in existing_codes:
                msgs.append("Bu student_code allaqachon mavjud")
            if data.email.lower() in existing_student_emails:
                msgs.append("Bu email allaqachon talaba sifatida mavjud")
            elif data.email.lower() in existing_user_emails:
                msgs.append("Bu email allaqachon foydalanuvchi sifatida mavjud")
            if msgs:
                add_error(row_no, data.model_dump(), msgs)
                continue
            to_create.append((row_no, data))

        errors.sort(key=lambda e: e["row"])

        if errors and not skip_invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "BULK_VALIDATION_FAILED",
                    "message": "Faylda xatolar bor, hech qanday talaba yaratilmadi",
                    "errors": errors,
                },
            )
        if not to_create:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "BULK_NOTHING_TO_CREATE",
                    "message": "Yaratish uchun to'g'ri qator topilmadi",
                    "errors": errors,
                },
            )

        # 4-bosqich: bitta tranzaksiyada yaratish
        users: List[User] = []
        passwords: List[str] = []
        for _, data in to_create:
            plain_password = secrets.token_urlsafe(12)
            users.append(
                User(
                    email=data.email,
                    full_name=data.full_name,
                    role=UserRole.STUDENT,
                    password_hash=get_password_hash(plain_password),
                )
            )
            passwords.append(plain_password)

        try:
            db.add_all(users)
            db.flush()  # user.id olish uchun

            students: List[Student] = []
            for (_, data), user in zip(to_create, users):
                payload = data.model_dump()
                payload["user_id"] = user.id
                if not payload.get("avatar_url"):
                    payload["avatar_url"] = ANONYMOUS_AVATAR_URL
                students.append(Student(**payload))
            db.add_all(students)
            db.flush()  # student.id olish uchun

            created = [
                {
                    "row": row_no,
                    "id": st.id,
                    "student_code": st.student_code,
                    "email": st.email,
                    "full_name": st.full_name,
                }
                for (row_no, _), st in zip(to_create, students)
            ]
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ma'lumotlar bazasida dublikat topildi, qayta urinib ko'ring",
            )

        # Commit'dan keyin parollarni yuborish (SES ulanmaguncha logga chiqadi)
        for plain_password in passwords:
            StudentService._notify_password(plain_password)

        return {
            "total": len(rows),
            "created_count": len(created),
            "failed_count": len(errors),
            "created": created,
            "errors": errors,
        }
