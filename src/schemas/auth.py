from datetime import datetime
from typing import Annotated
from uuid import UUID

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, BeforeValidator, EmailStr, Field, PlainSerializer

from src.models.user import UserRole


def coerce_user_role(value) -> UserRole:
    if isinstance(value, UserRole):
        return value
    return UserRole.parse(value)


# Input: admin/ADMIN/Admin; output: always "admin" / "staff"
ApiUserRole = Annotated[
    UserRole,
    BeforeValidator(coerce_user_role),
    PlainSerializer(lambda role: UserRole.parse(role).value, return_type=str),
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: ApiUserRole
    created_at: datetime

    class Config:
        from_attributes = True

