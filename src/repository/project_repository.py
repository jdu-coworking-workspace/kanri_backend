from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy import or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload

from src.models.project import Project, ProjectStatus, ProjectCategory
from src.models.project_member import ProjectMember
from src.models.student import Student


class ProjectRepository:
    
    @staticmethod
    def get_by_id(db: Session, project_id: UUID) -> Optional[Project]:
        return (
            db.query(Project)
            .options(
                joinedload(Project.leader),
                joinedload(Project.members).joinedload(ProjectMember.student)
            )
            .filter(Project.id == project_id)
            .first()
        )

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Project]:
        return db.query(Project).filter(Project.name == name).first()

    @staticmethod
    def get_list(
        db: Session,
        page: int,
        limit: int,
        name: Optional[str] = None,
        member: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        category: Optional[ProjectCategory] = None,
    ) -> Tuple[List[Project], int]:
        
        query = db.query(Project).options(
            joinedload(Project.leader),
            joinedload(Project.members).joinedload(ProjectMember.student)
        )

        if name:
            query = query.filter(Project.name.ilike(f"%{name}%"))
            
        if status:
            query = query.filter(Project.status == status)
            
        if category:
            query = query.filter(Project.category == category)
            
        if member:
            search = f"%{member}%"
            query = query.join(Project.members).join(ProjectMember.student).filter(
                or_(
                    Student.full_name.ilike(search),
                    Student.student_code.ilike(search)
                )
            ).distinct() # Distinct is necessary because join might return duplicate projects

        total = query.count()
        items = (
            query.order_by(Project.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def create(db: Session, project_data: dict) -> Project:
        project = Project(**project_data)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def update(db: Session, project: Project, update_data: dict) -> Project:
        for field, value in update_data.items():
            setattr(project, field, value)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        db.delete(project)
        db.commit()
