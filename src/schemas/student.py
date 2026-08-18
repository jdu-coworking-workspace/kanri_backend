# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

from src.models.student import SemesterEnum, SkillRank, WorkStatus


class StudentBaseSchema(BaseModel):
    full_name: str = Field(..., max_length=255)
    kana_name: str = Field(..., max_length=255)
    student_code: str = Field(..., max_length=50)
    email: EmailStr
    avatar_url: Optional[str] = Field(None, max_length=500)
    grad_year_month: Optional[date] = None
    semester: Optional[SemesterEnum] = None
    skill_rank: Optional[SkillRank] = None
    work_status: Optional[WorkStatus] = None
    point_1: Optional[int] = 0
    point_2: Optional[int] = 0
    point_3: Optional[int] = 0


class StudentCreateSchema(StudentBaseSchema):
    pass


class StudentUpdateSchema(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    kana_name: Optional[str] = Field(None, max_length=255)
    student_code: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = Field(None, max_length=500)
    grad_year_month: Optional[date] = None
    semester: Optional[SemesterEnum] = None
    skill_rank: Optional[SkillRank] = None
    work_status: Optional[WorkStatus] = None
    point_1: Optional[int] = None
    point_2: Optional[int] = None
    point_3: Optional[int] = None


class StudentCopySchema(BaseModel):
    student_code: str = Field(..., max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)
    kana_name: Optional[str] = Field(None, max_length=255)


class StudentOutSchema(StudentBaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentListSchema(BaseModel):
    items: List[StudentOutSchema]
    total: int
    page: int
    limit: int
