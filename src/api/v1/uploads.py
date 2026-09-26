from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_admin
from src.database.session import get_db
from src.models.user import User, UserRole
from src.models.student import Student
from src.repository.student_repository import StudentRepository
from src.utils.s3 import delete_avatar, upload_avatar

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def _read_avatar_file(file: UploadFile) -> tuple[bytes, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"Faqat {', '.join(ALLOWED_CONTENT_TYPES)} formatlar qabul qilinadi",
            },
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Fayl hajmi {MAX_FILE_SIZE_MB} MB dan oshmasligi kerak",
            },
        )
    return file_bytes, str(file.content_type)


def _store_avatar(db: Session, student: Student, file_bytes: bytes, content_type: str) -> str:
    if student.avatar_url:
        delete_avatar(str(student.avatar_url))

    file_url = upload_avatar(
        file_bytes=file_bytes,
        content_type=content_type,
        student_id=str(student.id),
    )
    student.avatar_url = file_url  # type: ignore[assignment]
    db.commit()
    db.refresh(student)
    return file_url


@router.post(
    "/me/avatar",
    status_code=status.HTTP_200_OK,
    summary="Joriy talaba o'z avatarini yuklaydi",
)
async def upload_own_avatar(
    file: UploadFile = File(..., description="Rasm fayli (JPEG, PNG, WEBP, max 5 MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if UserRole.parse(current_user.role) is not UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizda bu amalni bajarish uchun ruxsat yo'q",
        )

    student = StudentRepository.get_by_user_id(db, current_user.id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDENT_PROFILE_NOT_FOUND", "message": "Talaba profili topilmadi"},
        )

    file_bytes, content_type = await _read_avatar_file(file)
    file_url = _store_avatar(db, student, file_bytes, content_type)
    return {
        "success": True,
        "data": {
            "student_id": str(student.id),
            "file_url": file_url,
        },
    }


@router.post(
    "/avatar",
    status_code=status.HTTP_200_OK,
    summary="Talaba avatarini S3 ga yuklash (Faqat adminlar)",
    description=(
        "Fayl multipart/form-data sifatida yuboriladi. "
        "Backend faylni S3 ga yuklab, public URL ni qaytaradi. "
        "Qaytgan `file_url` ni `PUT /students/{id}` orqali `avatar_url` maydoniga saqlang."
    ),
)
async def upload_student_avatar(
    student_id: UUID = Form(..., description="Avatar yuklanadigan talaba ID si"),
    file: UploadFile = File(..., description="Rasm fayli (JPEG, PNG, WEBP, max 5 MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDENT_NOT_FOUND", "message": "Talaba topilmadi"},
        )

    file_bytes, content_type = await _read_avatar_file(file)
    file_url = _store_avatar(db, student, file_bytes, content_type)
    return {
        "success": True,
        "data": {
            "student_id": str(student_id),
            "file_url": file_url,
        },
    }
