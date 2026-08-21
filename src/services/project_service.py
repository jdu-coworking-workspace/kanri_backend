from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

# pyrefly: ignore [missing-import]
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.project_history import ProjectHistory
from src.models.project_member import ProjectMember
from src.models.student import Student
from src.models.project import Project, ProjectStatus, ProjectCategory
from src.repository.project_repository import ProjectRepository
from src.schemas.project import ProjectCreateSchema, ProjectUpdateSchema
from src.services.student_service import StudentService

MAX_PROJECT_MEMBERS = 8


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
        return ProjectRepository.get_list(
            db, page, limit, name, member, status, category
        )

    @staticmethod
    def _ensure_unique(
        db: Session, name: str, exclude_id: Optional[UUID] = None
    ) -> None:
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
    def create_project(
        db: Session, project_data: ProjectCreateSchema, user_id: UUID
    ) -> Project:
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
            ProjectService._ensure_unique(
                db, update_data["name"], UUID(str(project.id))
            )

        if (
            "leader_student_id" in update_data
            and update_data["leader_student_id"] != project.leader_student_id
        ):
            ProjectService._check_leader_exists(db, update_data["leader_student_id"])

        return ProjectRepository.update(db, project, update_data)

    @staticmethod
    def delete_project(db: Session, project_id: UUID) -> None:
        project = ProjectService.get_project(db, project_id)
        ProjectRepository.delete(db, project)

    @staticmethod
    def _get_active_member_count(db: Session, project_id: UUID) -> int:
        return (
            db.query(func.count(ProjectMember.id))
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.left_at.is_(None),
            )
            .scalar()
        )

    @staticmethod
    def _get_active_membership(
        db: Session, project_id: UUID, student_id: UUID
    ) -> Optional[ProjectMember]:
        return (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.student_id == student_id,
                ProjectMember.left_at.is_(None),
            )
            .first()
        )

    @staticmethod
    def add_member(
        db: Session,
        project_id: UUID,
        student_id: UUID,
        is_leader: bool,
        changed_by: UUID,
    ) -> ProjectMember:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROJECT_NOT_FOUND", "message": "Loyiha topilmadi"},
            )

        student = db.query(Student).filter(Student.id == student_id).first()
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STUDENT_NOT_FOUND", "message": "Talaba topilmadi"},
            )

        if (
            ProjectService._get_active_membership(db, project_id, student_id)
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ALREADY_MEMBER",
                    "message": "Talaba allaqachon loyiha a'zosi",
                },
            )

        if (
            ProjectService._get_active_member_count(db, project_id)
            >= MAX_PROJECT_MEMBERS
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "MEMBER_LIMIT_EXCEEDED",
                    "message": f"Loyihada a'zolar soni {MAX_PROJECT_MEMBERS} tadan oshmasligi kerak",
                },
            )

        member = ProjectMember(
            project_id=project_id,
            student_id=student_id,
            is_leader=is_leader,
            joined_at=datetime.utcnow(),
        )
        db.add(member)
        db.add(
            ProjectHistory(
                project_id=project_id,
                changed_by=changed_by,
                change_type="member_added",
                description=f"{student.full_name} loyihaga qo'shildi",
            )
        )

        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(
        db: Session, project_id: UUID, student_id: UUID, changed_by: UUID
    ) -> None:
        membership = ProjectService._get_active_membership(db, project_id, student_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "MEMBERSHIP_NOT_FOUND",
                    "message": "Faol a'zolik topilmadi",
                },
            )

        membership.left_at = datetime.utcnow()  # type: ignore[assignment]
        db.add(membership)
        db.add(
            ProjectHistory(
                project_id=project_id,
                changed_by=changed_by,
                change_type="member_removed",
                description=f"Talaba (id={student_id}) loyihadan olib tashlandi",
            )
        )

        db.commit()

    @staticmethod
    def move_member(
        db: Session,
        project_id: UUID,
        student_id: UUID,
        target_project_id: UUID,
        changed_by: UUID,
    ) -> ProjectMember:
        if project_id == target_project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SAME_PROJECT",
                    "message": "Manba va maqsad loyihalar bir xil bo'lishi mumkin emas",
                },
            )

        target_project = (
            db.query(Project).filter(Project.id == target_project_id).first()
        )
        if target_project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TARGET_PROJECT_NOT_FOUND",
                    "message": "Maqsad loyiha topilmadi",
                },
            )

        try:
            source_membership = ProjectService._get_active_membership(
                db, project_id, student_id
            )
            if source_membership is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "MEMBERSHIP_NOT_FOUND",
                        "message": "Talaba joriy loyihada faol a'zo emas",
                    },
                )

            if (
                ProjectService._get_active_membership(db, target_project_id, student_id)
                is not None
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ALREADY_MEMBER",
                        "message": "Talaba maqsad loyihada allaqachon a'zo",
                    },
                )

            if (
                ProjectService._get_active_member_count(db, target_project_id)
                >= MAX_PROJECT_MEMBERS
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "MEMBER_LIMIT_EXCEEDED",
                        "message": f"Maqsad loyihada a'zolar soni {MAX_PROJECT_MEMBERS} tadan oshmasligi kerak",
                    },
                )

            now = datetime.utcnow()
            source_membership.left_at = now  # type: ignore[assignment]
            db.add(source_membership)

            new_membership = ProjectMember(
                project_id=target_project_id,
                student_id=student_id,
                is_leader=False,
                joined_at=now,
            )
            db.add(new_membership)

            db.add_all(
                [
                    ProjectHistory(
                        project_id=project_id,
                        changed_by=changed_by,
                        change_type="member_moved_out",
                        description=f"Talaba (id={student_id}) {target_project_id} loyihasiga ko'chirildi",
                    ),
                    ProjectHistory(
                        project_id=target_project_id,
                        changed_by=changed_by,
                        change_type="member_moved_in",
                        description=f"Talaba (id={student_id}) {project_id} loyihasidan ko'chirib keltirildi",
                    ),
                ]
            )

            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(new_membership)
        return new_membership
