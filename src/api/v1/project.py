from typing import Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_admin
from src.database.session import get_db
from src.models.project import ProjectStatus, ProjectCategory
from src.models.user import User
from src.schemas.project import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ProjectListOutSchema,
)
from src.services.project_service import ProjectService

router = APIRouter()


@router.get(
    "/",
    response_model=ProjectListOutSchema,
    summary="Loyihalar ro'yxati",
    description="Loyihalar ro'yxatini pagination va filterlar (nomi, a'zo, holat, kategoriya) bilan olish",
)
def get_projects(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    limit: int = Query(10, ge=1, le=100, description="Sahifadagi yozuvlar soni"),
    name: Optional[str] = Query(None, description="Loyiha nomi bo'yicha qidiruv"),
    member: Optional[str] = Query(None, description="A'zo ismi yoki kodi bo'yicha qidiruv"),
    status: Optional[ProjectStatus] = Query(None, description="Loyiha holati"),
    category: Optional[ProjectCategory] = Query(None, description="Loyiha kategoriyasi"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects, total = ProjectService.get_projects(
        db=db,
        page=page,
        limit=limit,
        name=name,
        member=member,
        status=status,
        category=category,
    )

    return {
        "success": True,
        "data": projects,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "has_next": (page * limit) < total,
            "has_prev": page > 1,
        },
    }


@router.get(
    "/{id}",
    summary="Bitta loyiha haqida ma'lumot",
)
def get_project(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.get_project(db, id)
    return {
        "success": True,
        "data": project
    }


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Yangi loyiha yaratish (Faqat muharrirlar)",
)
def create_project(
    project_in: ProjectCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = ProjectService.create_project(db, project_in, current_user.id)
    return {
        "success": True,
        "data": project
    }


@router.put(
    "/{id}",
    summary="Loyihani tahrirlash (Faqat muharrirlar)",
)
def update_project(
    id: UUID,
    project_in: ProjectUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = ProjectService.update_project(db, id, project_in)
    return {
        "success": True,
        "data": project
    }


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Loyihani o'chirish (Faqat muharrirlar)",
)
def delete_project(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ProjectService.delete_project(db, id)
