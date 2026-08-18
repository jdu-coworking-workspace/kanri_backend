"""
Barcha testlar uchun umumiy conftest.py — PostgreSQL test DB

Strategiya:
- TEST_DATABASE_URL (.env) orqali alohida 'cowork_test_db' ishlatiladi
- Har bir test SESSION boshida jadvallar yaratiladi (create_all)
- Har bir test FUNKSIYASI ichida tranzaksiya ochiladi va rollback qilinadi
  → testlar bir-birini iflositlamaydi, hech narsa DB'da qolmaydi
- Session oxirida jadvallar o'chiriladi (drop_all)
"""
import os
import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, text
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker

from src.main import app
# Barcha modellarni import — Base.metadata'ga ro'yxatdan o'tkazish uchun
from src.models import User, Student, Project, ProjectMember, ProjectHistory  # noqa: F401
from src.models.base import Base
from src.database.session import get_db
from src.utils.security import get_password_hash

# ─── Test DB engine ────────────────────────────────────────────────────────────
# .env dan TEST_DATABASE_URL o'qiladi (fallback: DATABASE_URL)
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/cowork_test_db"),
)

engine = create_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Session-scope: jadvallarni bir marta yaratib, oxirida o'chirish ──────────

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Test sessiyasi boshida sxema yaratiladi, oxirida o'chiriladi."""
    Base.metadata.drop_all(bind=engine)   # eskisini tozalash
    Base.metadata.create_all(bind=engine) # yangi sxema
    yield
    Base.metadata.drop_all(bind=engine)   # test tugagandan keyin tozalash


# ─── Function-scope: har bir test izolyatsiyalangan tranzaksiyada ─────────────

@pytest.fixture(scope="function")
def test_db(setup_test_database):
    """
    Har bir test uchun alohida tranzaksiya.
    Test tugaganda ROLLBACK — DB'da hech narsa qolmaydi.
    """
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI TestClient — get_db dependency override qilingan."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ─── User fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(test_db) -> User:
    """Tahrirlash huquqiga ega xodim (role='admin')."""
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("secret123"),
        full_name="Admin Xodim",
        role="admin",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def staff_user(test_db) -> User:
    """Faqat ko'rish huquqiga ega xodim (role='staff')."""
    user = User(
        email="staff@test.com",
        password_hash=get_password_hash("secret123"),
        full_name="Staff Xodim",
        role="staff",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_cookie(client, admin_user) -> str:
    """Admin login qilib access_token cookie'sini qaytaradi."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "secret123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.cookies["access_token"]


@pytest.fixture
def staff_cookie(client, staff_user) -> str:
    """Staff login qilib access_token cookie'sini qaytaradi."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "staff@test.com", "password": "secret123"},
    )
    assert resp.status_code == 200, f"Staff login failed: {resp.text}"
    return resp.cookies["access_token"]


# ─── Domain fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_student(test_db) -> Student:
    """Test uchun tayyor talaba yozuvi."""
    student = Student(
        full_name="Karimova Nilufar",
        kana_name="カリモワ",
        student_code="UZ240001",
        email="nilufar@test.com",
        skill_rank="A",
        work_status="active",
    )
    test_db.add(student)
    test_db.commit()
    test_db.refresh(student)
    return student


@pytest.fixture
def sample_project(test_db, admin_user) -> Project:
    """Test uchun tayyor loyiha yozuvi."""
    from datetime import date
    project = Project(
        name="Test Loyiha",
        start_date=date(2026, 1, 1),
        status="active",
        category="it",
        created_by=admin_user.id,
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project
