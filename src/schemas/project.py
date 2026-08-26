from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from src.models.project import ProjectStatus, ProjectCategory
from src.schemas.student import StudentOutSchema


class ProjectBaseSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Loyihaning nomi")
    overview: Optional[str] = Field(None, description="Loyiha haqida qisqacha ma'lumot")
    start_date: date = Field(..., description="Loyiha boshlanish sanasi")
    end_date: Optional[date] = Field(None, description="Loyiha tugash sanasi")
    status: ProjectStatus = Field(ProjectStatus.PLANNED, description="Loyiha holati")
    category: ProjectCategory = Field(..., description="Loyiha kategoriyasi")
    leader_student_id: Optional[UUID] = Field(
        None, description="Loyiha rahbari (Student ID)"
    )


class ProjectCreateSchema(ProjectBaseSchema):
    pass


class ProjectUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    overview: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None
    category: Optional[ProjectCategory] = None
    leader_student_id: Optional[UUID] = None


class ProjectMemberSimpleSchema(BaseModel):
    id: UUID
    student: StudentOutSchema
    is_leader: bool
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectOutSchema(ProjectBaseSchema):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    leader: Optional[StudentOutSchema] = None
    members: Optional[List[ProjectMemberSimpleSchema]] = None

    class Config:
        from_attributes = True


class ProjectListOutSchema(BaseModel):
    success: bool = True
    data: List[ProjectOutSchema]
    meta: dict


class ProjectMemberAddSchema(BaseModel):
    student_id: UUID = Field(..., description="Loyihaga qo'shiladigan talaba ID si")
    is_leader: bool = Field(False, description="Loyiha rahbari sifatida belgilash")


class ProjectMemberMoveSchema(BaseModel):
    target_project_id: UUID = Field(
        ..., description="Talaba ko'chiriladigan loyiha ID si"
    )


class ProjectHistoryOutSchema(BaseModel):
    id: UUID
    project_id: UUID
    changed_by: UUID
    change_type: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
