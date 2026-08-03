from enum import Enum
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Date, Integer, Enum as SQLEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from .base import Base, TimeStampsMixin, generate_uuid

class SkillRank(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"

class WorkStatus(str, Enum):
    ACTIVE = "active"
    INTERN = "intern"
    ON_LEAVE = "on_leave"

class SemesterEnum(str, Enum):
    SEMESTER_1 = "1-semestr"
    SEMESTER_2 = "2-semestr"
    SEMESTER_3 = "3-semestr"
    SEMESTER_4 = "4-semestr"
    SEMESTER_5 = "5-semestr"
    SEMESTER_6 = "6-semestr"
    SEMESTER_7 = "7-semestr"
    SEMESTER_8 = "8-semestr"
    SEMESTER_9 = "9-semestr"

class Student(Base, TimeStampsMixin):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    full_name = Column(String(255), nullable=False)
    kana_name = Column(String(255), nullable=False)
    student_code = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    grad_year_month = Column(Date, nullable=True)

    semester = Column(SQLEnum(SemesterEnum), nullable=True)
    skill_rank = Column(SQLEnum(SkillRank), nullable=True)
    work_status = Column(SQLEnum(WorkStatus), nullable=True)

    point_1 = Column(Integer, default=0)
    point_2 = Column(Integer, default=0)
    point_3 = Column(Integer, default=0)

    project_memberships = relationship("ProjectMember", back_populates="student", cascade="all, delete-orphan")

    @property
    def concurrent_projects_count(self):
        return len([pm for pm in self.project_memberships if pm.left_at is None])

