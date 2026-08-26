from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.database.session import get_db
from src.models.user import User
from src.models.student import Student
from src.utils.s3 import delete_avatar, upload_avatar

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


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
    # 1. Content-type tekshiruvi
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"Faqat {', '.join(ALLOWED_CONTENT_TYPES)} formatlar qabul qilinadi",
            },
        )

    # 2. Fayl hajmi tekshiruvi
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Fayl hajmi {MAX_FILE_SIZE_MB} MB dan oshmasligi kerak",
            },
        )

    # 3. Talaba mavjudligini tekshirish
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDENT_NOT_FOUND", "message": "Talaba topilmadi"},
        )

    # 4. Eski avatarni o'chirish (agar mavjud bo'lsa)
    if student.avatar_url:
        delete_avatar(str(student.avatar_url))

    # 5. Yangi faylni S3 ga yuklash
    file_url = upload_avatar(
        file_bytes=file_bytes,
        content_type=str(file.content_type),
        student_id=str(student_id),
    )

    # 6. avatar_url ni DBda yangilash
    student.avatar_url = file_url  # type: ignore[assignment]
    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "data": {
            "student_id": str(student_id),
            "file_url": file_url,
        },
    }
