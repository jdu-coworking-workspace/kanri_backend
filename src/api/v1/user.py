from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.database.session import get_db
from src.models.user import User
from src.schemas.auth import UserOut
from src.schemas.user import (
    UserCreateSchema,
    UserRoleUpdateSchema,
    UserListOutSchema,
)
from src.services.user_service import UserService

router = APIRouter()


@router.get(
    "/",
    response_model=UserListOutSchema,
    summary="Barcha xodimlarni olish (Faqat admin)",
)
def get_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    users = UserService.get_users(db)
    return {
        "success": True,
        "data": users
    }


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Yangi xodim qo'shish (Faqat admin)",
)
def create_user(
    user_in: UserCreateSchema,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = UserService.create_user(db, user_in)
    return {
        "success": True,
        "data": user
    }


@router.put(
    "/{id}/role",
    summary="Xodimning rolini o'zgartirish (Faqat admin)",
)
def update_user_role(
    id: UUID,
    role_in: UserRoleUpdateSchema,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = UserService.update_role(db, id, role_in)
    return {
        "success": True,
        "data": user
    }


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xodimni o'chirish (Faqat admin)",
)
def delete_user(
    id: UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    UserService.delete_user(db, id, current_admin.id)
