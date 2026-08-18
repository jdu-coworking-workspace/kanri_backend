from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.models.project import Project, ProjectStatus, ProjectCategory
from src.repository.project_repository import ProjectRepository
from src.schemas.project import ProjectCreateSchema, ProjectUpdateSchema
from src.services.student_service import StudentService


class ProjectService:

    @staticmethod
    def get_project(db: Session, project_id: UUID) -> Project:
        project = ProjectRepository.get_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loyiha topilmadi",
            )
        return project

    @staticmethod
    def get_projects(
        db: Session,
        page: int,
        limit: int,
        name: Optional[str] = None,
        member: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        category: Optional[ProjectCategory] = None,
    ) -> Tuple[List[Project], int]:
        if page < 1:
            page = 1
        if limit < 1:
            limit = 10
        return ProjectRepository.get_list(db, page, limit, name, member, status, category)

    @staticmethod
    def _ensure_unique(db: Session, name: str, exclude_id: Optional[UUID] = None) -> None:
        existing = ProjectRepository.get_by_name(db, name)
        if existing and str(existing.id) != str(exclude_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bunday nomli loyiha allaqachon mavjud",
            )

    @staticmethod
    def _check_leader_exists(db: Session, leader_student_id: Optional[UUID]) -> None:
        if leader_student_id:
            try:
                StudentService.get_student(db, leader_student_id)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Loyiha rahbari sifatida ko'rsatilgan talaba topilmadi",
                )

    @staticmethod
    def create_project(db: Session, project_data: ProjectCreateSchema, user_id: UUID) -> Project:
        ProjectService._ensure_unique(db, project_data.name)
        ProjectService._check_leader_exists(db, project_data.leader_student_id)
        
        data = project_data.model_dump()
        data["created_by"] = user_id
        
        return ProjectRepository.create(db, data)

    @staticmethod
    def update_project(
        db: Session,
        project_id: UUID,
        project_data: ProjectUpdateSchema,
    ) -> Project:
        project = ProjectService.get_project(db, project_id)
        update_data = project_data.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != project.name:
            ProjectService._ensure_unique(db, update_data["name"], UUID(str(project.id)))

        if "leader_student_id" in update_data and update_data["leader_student_id"] != project.leader_student_id:
            ProjectService._check_leader_exists(db, update_data["leader_student_id"])

        return ProjectRepository.update(db, project, update_data)

    @staticmethod
    def delete_project(db: Session, project_id: UUID) -> None:
        project = ProjectService.get_project(db, project_id)
        ProjectRepository.delete(db, project)
