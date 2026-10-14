# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.schemas.auth import ChangePasswordRequest, LoginRequest
from src.repository import user_repository
from src.models.user import User, UserRole
from src.utils.security import verify_password, create_access_token, get_password_hash

def authenticate_user(db: Session, login_data: LoginRequest):
    user = user_repository.get_user_by_email(db, login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email yoki parol noto'g'ri"
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email yoki parol noto'g'ri"
        )
    
    token = create_access_token(
        subject=user.id,
        role=UserRole.parse(user.role).value,
    )

    return user, token


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WRONG_CURRENT_PASSWORD",
                "message": "Joriy parol noto'g'ri",
            },
        )

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PASSWORD_UNCHANGED",
                "message": "Yangi parol joriy parol bilan bir xil",
            },
        )

    user_repository.update_password(db, user, get_password_hash(payload.new_password))

    




