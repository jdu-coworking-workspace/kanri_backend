# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.models.user import User, UserRole

import uuid

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str | uuid.UUID) -> User | None:
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.role != UserRole.STUDENT)
        .order_by(User.created_at.desc())
        .all()
    )

def create_user(db: Session, user_data: dict) -> User:
    payload = dict(user_data)
    if "role" in payload:
        payload["role"] = UserRole.parse(payload["role"])
    user = User(**payload)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_password(db: Session, user: User, password_hash: str) -> User:
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user


def update_user_role(db: Session, user: User, role: str | UserRole) -> User:
    user.role = UserRole.parse(role)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
