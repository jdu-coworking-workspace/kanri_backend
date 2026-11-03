from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy import or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload, selectinload

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
                selectinload(Project.members).joinedload(ProjectMember.student)
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
            selectinload(Project.members).joinedload(ProjectMember.student)
        )

        if name and name.strip():
            query = query.filter(Project.name.ilike(f"%{name.strip()}%"))
            
        if status:
            query = query.filter(Project.status == status)
            
        if category:
            query = query.filter(Project.category == category)
            
        if member and member.strip():
            search = f"%{member.strip()}%"
            # Search active members (left_at is NULL) or project leader without joining Project.members
            # directly into main query, preventing member list corruption and pagination bugs
            query = query.filter(
                or_(
                    db.query(ProjectMember)
                    .join(Student, Student.id == ProjectMember.student_id)
                    .filter(
                        ProjectMember.project_id == Project.id,
                        ProjectMember.left_at.is_(None),
                        or_(
                            Student.full_name.ilike(search),
                            Student.student_code.ilike(search),
                            Student.kana_name.ilike(search),
                        )
                    )
                    .exists(),
                    db.query(Student)
                    .filter(
                        Student.id == Project.leader_student_id,
                        or_(
                            Student.full_name.ilike(search),
                            Student.student_code.ilike(search),
                            Student.kana_name.ilike(search),
                        )
                    )
                    .exists()
                )
            )

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
