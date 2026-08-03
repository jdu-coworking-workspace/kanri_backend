from enum import Enum
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Date, ForeignKey, Text, Enum as SQLEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship 
from .base import Base, TimeStampsMixin, generate_uuid

class ProjectStatus(str, Enum):
    DONE = "done"
    ACTIVE = "active"
    PLANNED = "planned"
    CANCELLED = "cancelled"
    
class ProjectCategory(str, Enum):
    IT = "it"
    VIDEO = "video"
    LIGHT_WORK = "light_work"
    COWORK = "cowork" 
    TRIAL = "trial"   



class Project(Base, TimeStampsMixin):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    overview = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    status = Column(SQLEnum(ProjectStatus), nullable=False, default=ProjectStatus.PLANNED)
    category = Column(SQLEnum(ProjectCategory), nullable=False)

    leader_student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    creator = relationship("User", foreign_keys=[created_by])
    leader = relationship("Student", foreign_keys=[leader_student_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")