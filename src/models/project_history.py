# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class ProjectHistory(Base):
    __tablename__ = "project_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    change_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)