from typing import List, Optional
from uuid import UUID
from datetime import datetime

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field

from src.models.user import UserRole
from src.schemas.auth import UserOut


class UserCreateSchema(BaseModel):
    email: EmailStr = Field(..., description="Foydalanuvchi elektron pochtasi")
    password: str = Field(..., min_length=6, description="Foydalanuvchi paroli")
    full_name: str = Field(..., max_length=255, description="Foydalanuvchi to'liq ismi")
    role: UserRole = Field(UserRole.STAFF, description="Foydalanuvchi roli")


class UserRoleUpdateSchema(BaseModel):
    role: UserRole = Field(..., description="Yangi rol")


class UserListOutSchema(BaseModel):
    success: bool = True
    data: List[UserOut]
