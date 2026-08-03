# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Boolean
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID 
from .base import Base, TimeStampsMixin, generate_uuid

class User(Base, TimeStampsMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_editor = Column(Boolean, default=False, nullable=False)
