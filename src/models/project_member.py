# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Index
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, generate_uuid

class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    is_leader = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
    
    project = relationship("Project", back_populates="members")
    student = relationship("Student", back_populates="project_memberships")

    __table_args__ = (
        Index('uq_active_member', 'project_id', 'student_id', unique=True, postgresql_where=(left_at.is_(None))),
    )
