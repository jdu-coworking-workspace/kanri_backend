# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_editor: bool
    created_at: datetime

    class Config:
        from_attributes = True

