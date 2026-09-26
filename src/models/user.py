from enum import Enum
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Enum as SQLEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimeStampsMixin, generate_uuid


class UserRole(str, Enum):
    """API/JWT qiymatlari kichik harf: staff, admin, student.

    PostgreSQL `userrole` enum esa Alembic migratsiyasida
    STAFF/ADMIN/STUDENT (enum name) sifatida yaratilgan. SQLAlchemy
    `values_callable` shu nomlarni saqlaydi, Python/JSON esa
    `.value` ni qaytaradi.
    """

    STAFF = "staff"
    ADMIN = "admin"
    STUDENT = "student"

    @classmethod
    def try_parse(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            key = value.strip().lower()
            for member in cls:
                if member.value == key or member.name.lower() == key:
                    return member
        return None

    @classmethod
    def parse(cls, value) -> "UserRole":
        parsed = cls.try_parse(value)
        if parsed is None:
            raise ValueError(f"Unknown user role: {value!r}")
        return parsed

    @classmethod
    def _missing_(cls, value):
        return cls.try_parse(value)


def _user_role_db_values(enum_cls):
    return [member.name for member in enum_cls]


class User(Base, TimeStampsMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(
            UserRole,
            name="userrole",
            native_enum=True,
            values_callable=_user_role_db_values,
            validate_strings=True,
        ),
        default=UserRole.STAFF,
        nullable=False,
    )

    @property
    def is_admin(self) -> bool:
        return UserRole.parse(self.role) is UserRole.ADMIN

    @property
    def is_student(self) -> bool:
        return UserRole.parse(self.role) is UserRole.STUDENT
