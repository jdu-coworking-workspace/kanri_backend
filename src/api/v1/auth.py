# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Response
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.schemas.auth import LoginRequest, UserOut
from src.services.auth_service import authenticate_user
# pyrefly: ignore [missing-import]
from src.api.deps import get_db, get_current_user
from src.models.user import User
from src.config import settings

router = APIRouter()

@router.post("/login")
def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    user, token = authenticate_user(db, login_data)

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=(settings.APP_ENV == "production"),
        samesite="lax",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/"
    )

    return {
        "success": True,
        "data": {
            "user": UserOut.model_validate(user)
        }
    }


@router.post("/logout")
def logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/"
    )

    return {
        "success": True
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "user": UserOut.model_validate(current_user)
        }
    }