# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.schemas.auth import LoginRequest
from src.repository import user_repository
from src.utils.security import verify_password, create_access_token

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
    
    token = create_access_token(subject=user.id, role=user.role.value)

    return user, token

    




