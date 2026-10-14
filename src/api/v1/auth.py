# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Response
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.schemas.auth import ChangePasswordRequest, LoginRequest, UserOut
from src.services.auth_service import authenticate_user, change_password
# pyrefly: ignore [missing-import]
from src.api.deps import get_db, get_current_user
from src.models.user import User
from src.config import settings

router = APIRouter()


def _cookie_secure() -> bool:
    if settings.COOKIE_SECURE is None:
        return settings.APP_ENV == "production"
    return settings.COOKIE_SECURE


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure(),
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


@router.post("/login")
def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    user, token = authenticate_user(db, login_data)
    _set_auth_cookie(response, token)

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
    _clear_auth_cookie(response)

    return {
        "success": True
    }


@router.post("/change-password")
def update_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    change_password(db, current_user, payload)
    return {"success": True}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "user": UserOut.model_validate(current_user)
        }
    }