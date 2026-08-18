# pyrefly: ignore [missing-import]
from fastapi import Depends, HTTPException, status, Request

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

# pyrefly: ignore [missing-import]
from src.database.session import get_db

# pyrefly: ignore [missing-import]
from src.utils.security import decode_access_token
from src.repository import user_repository
from src.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token topilmadi (Tizimga kirmagansiz)",
        )

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz yoki muddati o'tgan token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ichida foydalanuvchi ma'lumoti yo'q",
        )

    user = user_repository.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi"
        )

    return user


def require_editor(current_user: User = Depends(get_current_user)) -> User:
    if not current_user["is_editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizda bu amalni bajarish uchun ruxsat yo'q",
        )
    return current_user
