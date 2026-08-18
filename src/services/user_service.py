from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.repository import user_repository
from src.schemas.user import UserCreateSchema, UserRoleUpdateSchema
from src.utils.security import get_password_hash


class UserService:

    @staticmethod
    def get_users(db: Session) -> List[User]:
        return user_repository.get_users(db)

    @staticmethod
    def get_user(db: Session, user_id: UUID) -> User:
        user = user_repository.get_user_by_id(db, str(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Foydalanuvchi topilmadi",
            )
        return user

    @staticmethod
    def create_user(db: Session, user_data: UserCreateSchema) -> User:
        existing = user_repository.get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu elektron pochta orqali foydalanuvchi allaqachon ro'yxatdan o'tgan",
            )
            
        new_user_data = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "role": user_data.role,
            "password_hash": get_password_hash(user_data.password)
        }
        
        return user_repository.create_user(db, new_user_data)

    @staticmethod
    def update_role(db: Session, user_id: UUID, role_data: UserRoleUpdateSchema) -> User:
        user = UserService.get_user(db, user_id)
        return user_repository.update_user_role(db, user, role_data.role)

    @staticmethod
    def delete_user(db: Session, user_id: UUID, current_user_id: UUID) -> None:
        if str(user_id) == str(current_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O'zingizni o'chira olmaysiz",
            )
            
        user = UserService.get_user(db, user_id)
        user_repository.delete_user(db, user)
