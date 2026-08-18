from typing import Optional, List, Tuple
from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy import or_

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload
# pyrefly: ignore [missing-import]
from src.models.project_member import ProjectMember

from src.models.student import Student


class StudentRepository:

    @staticmethod
    def get_by_id(db: Session, student_id: UUID) -> Optional[Student]:
        return db.query(Student).filter(Student.id == student_id).first()

    @staticmethod
    def get_by_student_code(db: Session, student_code: str) -> Optional[Student]:
        return db.query(Student).filter(Student.student_code == student_code).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Student]:
        return db.query(Student).filter(Student.email == email).first()

    @staticmethod
    def get_list(
        db: Session,
        page: int,
        limit: int,
        q: Optional[str] = None,
    ) -> Tuple[List[Student], int]:
        query = db.query(Student)

        if q:
            search = f"%{q}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(search),
                    Student.kana_name.ilike(search),
                    Student.student_code.ilike(search),
                )
            )

        total = query.count()
        items = (
            query.order_by(Student.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def create(db: Session, student_data: dict) -> Student:
        student = Student(**student_data)
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def update(db: Session, student: Student, update_data: dict) -> Student:
        for field, value in update_data.items():
            setattr(student, field, value)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def delete(db: Session, student: Student) -> None:
        db.delete(student)
        db.commit()

    @staticmethod
    def get_memberships(db: Session, student_id: UUID) -> List:
        return (
            db.query(ProjectMember)
            .options(joinedload(ProjectMember.project))
            .filter(ProjectMember.student_id == student_id)
            .order_by(ProjectMember.joined_at.desc())
            .all()
        )
