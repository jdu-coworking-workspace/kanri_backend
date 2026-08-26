import uuid
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

from src.config import settings

# Local rejimda fayllar saqlanadigan papka: backend/media/
MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "media"


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API — uploads.py faqat shu 2 funksiyani chaqiradi
# ──────────────────────────────────────────────────────────────────────────────

def upload_avatar(file_bytes: bytes, content_type: str, student_id: str) -> str:
    """
    S3_MODE ga qarab localga yoki S3 ga yuklaydi.
    Qaytadi: public URL string
    """
    if settings.S3_MODE == "production":
        return _upload_to_s3(file_bytes, content_type, student_id)
    return _upload_to_local(file_bytes, content_type, student_id)


def delete_avatar(avatar_url: str) -> None:
    """
    S3_MODE ga qarab localdan yoki S3 dan o'chiradi.
    Xatolik bo'lsa silent — asosiy jarayon to'xtatilmaydi.
    """
    if not avatar_url:
        return
    try:
        if settings.S3_MODE == "production":
            _delete_from_s3(avatar_url)
        else:
            _delete_from_local(avatar_url)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# LOCAL — backend/media/ papkasiga saqlash
# ──────────────────────────────────────────────────────────────────────────────

def _upload_to_local(file_bytes: bytes, content_type: str, student_id: str) -> str:
    ext = _get_extension(content_type)
    relative_path = f"avatars/{student_id}/{uuid.uuid4()}.{ext}"
    full_path = MEDIA_ROOT / relative_path

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)

    # Frontenddan kirish uchun URL: http://localhost:8000/media/avatars/...
    return f"/media/{relative_path}"


def _delete_from_local(avatar_url: str) -> None:
    # URL formatı: /media/avatars/...
    if not avatar_url.startswith("/media/"):
        return
    relative = avatar_url.removeprefix("/media/")
    full_path = MEDIA_ROOT / relative
    if full_path.exists():
        full_path.unlink()


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCTION — AWS S3 ga yuklash
# ──────────────────────────────────────────────────────────────────────────────

def _get_s3_client():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "S3_NOT_CONFIGURED",
                "message": "AWS S3 sozlamalari (AWS_ACCESS_KEY_ID, AWS_S3_BUCKET_NAME) to'ldirilmagan",
            },
        )
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _upload_to_s3(file_bytes: bytes, content_type: str, student_id: str) -> str:
    ext = _get_extension(content_type)
    key = f"avatars/{student_id}/{uuid.uuid4()}.{ext}"

    s3 = _get_s3_client()
    try:
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "S3_UPLOAD_FAILED",
                "message": f"S3 ga yuklash muvaffaqiyatsiz: {str(e)}",
            },
        )

    return (
        f"https://{settings.AWS_S3_BUCKET_NAME}"
        f".s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    )


def _delete_from_s3(avatar_url: str) -> None:
    key = _extract_s3_key(avatar_url)
    if not key:
        return
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    s3.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=key)


# ──────────────────────────────────────────────────────────────────────────────
# Yordamchi funksiyalar
# ──────────────────────────────────────────────────────────────────────────────

def _get_extension(content_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }.get(content_type, "jpg")


def _extract_s3_key(url: str) -> str:
    """https://bucket.s3.region.amazonaws.com/key dan key ni ajratib oladi."""
    parts = url.split(".amazonaws.com/", 1)
    return parts[1] if len(parts) == 2 else ""
