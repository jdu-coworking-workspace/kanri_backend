import uuid
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, DateTime
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def generate_uuid():
    return uuid.uuid4()

class TimeStampsMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)