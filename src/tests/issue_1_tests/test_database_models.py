"""
Issue 01: Ma'lumotlar bazasi modellari va Alembic migratsiyasi

Testlar quyidagilarni tekshiradi:
1. Barcha modellar mavjud va to'g'ri maydonlarga ega
2. Enum qiymatlari hujjatga mos
3. Ob'ektlar DB'ga yoziladi va o'qiladi
4. Relationships (bog'lanishlar) to'g'ri ishlaydi
5. Unikal cheklovlar ishlaydi (student_code, email)
6. CASCADE o'chirish ishlaydi
7. TimeStampsMixin created_at/updated_at ni to'ldiradi
"""
import uuid
# pyrefly: ignore [missing-import]
import pytest
from datetime import date, datetime

from src.models import User, Student, Project, ProjectMember, ProjectHistory
from src.models.student import SkillRank, WorkStatus, SemesterEnum
from src.models.project import ProjectStatus, ProjectCategory
from src.utils.security import get_password_hash


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MODEL STRUKTURASI TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserModel:
    """User modeli maydonlari va cheklovlari."""

    def test_user_table_name(self):
        assert User.__tablename__ == "users"

    def test_user_required_columns_exist(self):
        cols = {c.name for c in User.__table__.columns}
        assert {"id", "email", "password_hash", "full_name", "role",
                "created_at", "updated_at"}.issubset(cols)

    def test_user_email_is_unique(self):
        """email ustunida unique constraint bor."""
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True or any(
            "email" in str(c) for c in User.__table__.constraints
        )

    def test_user_role_default_staff(self):
        user = User(
            email="test@x.com",
            password_hash="hash",
            full_name="Test",
        )
        assert user.role is None or user.role == "staff"

    def test_user_create_and_read(self, test_db):
        """User DB'ga yoziladi va o'qiladi."""
        user = User(
            email="user1@test.com",
            password_hash=get_password_hash("pass"),
            full_name="Test User",
            role="admin",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        fetched = test_db.query(User).filter(User.email == "user1@test.com").first()
        assert fetched is not None
        assert fetched.full_name == "Test User"
        assert fetched.role == "admin"
        assert fetched.id is not None

    def test_user_timestamps_auto_populated(self, test_db):
        """created_at va updated_at avtomatik to'ldiriladi."""
        user = User(
            email="ts@test.com",
            password_hash="hash",
            full_name="Timestamp User",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_email_unique_constraint(self, test_db):
        """Bir xil email ikki marta qo'shilsa xato beradi."""
        # pyrefly: ignore [missing-import]
        from sqlalchemy.exc import IntegrityError

        user1 = User(email="dup@test.com", password_hash="h", full_name="U1")
        user2 = User(email="dup@test.com", password_hash="h", full_name="U2")
        test_db.add(user1)
        test_db.commit()
        test_db.add(user2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()


class TestStudentModel:
    """Student modeli maydonlari, enumlar va cheklovlar."""

    def test_student_table_name(self):
        assert Student.__tablename__ == "students"

    def test_student_required_columns_exist(self):
        cols = {c.name for c in Student.__table__.columns}
        expected = {
            "id", "full_name", "kana_name", "student_code", "email",
            "avatar_url", "semester", "skill_rank", "work_status",
            "grad_year_month", "point_1", "point_2", "point_3",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_skill_rank_enum_values(self):
        """SkillRank enum barcha 6 ta qiymatni o'z ichiga oladi."""
        values = {r.value for r in SkillRank}
        assert values == {"S", "A", "B", "C", "D", "E"}

    def test_work_status_enum_values(self):
        values = {s.value for s in WorkStatus}
        assert values == {"active", "intern", "on_leave"}

    def test_semester_enum_values(self):
        values = {s.value for s in SemesterEnum}
        assert len(values) == 9
        assert "1-semestr" in values
        assert "9-semestr" in values

    def test_student_create_and_read(self, test_db):
        """Student DB'ga yoziladi va o'qiladi."""
        student = Student(
            full_name="Karimova Nilufar",
            kana_name="カリモワ",
            student_code="UZ240001",
            email="nilufar@test.com",
            skill_rank=SkillRank.S,
            work_status=WorkStatus.ACTIVE,
            semester=SemesterEnum.SEMESTER_4,
            grad_year_month=date(2026, 6, 1),
            point_1=10, point_2=20, point_3=30,
        )
        test_db.add(student)
        test_db.commit()
        test_db.refresh(student)

        fetched = test_db.query(Student).filter(
            Student.student_code == "UZ240001"
        ).first()
        assert fetched is not None
        assert fetched.full_name == "Karimova Nilufar"
        assert fetched.skill_rank == SkillRank.S
        assert fetched.point_1 == 10

    def test_student_code_unique_constraint(self, test_db):
        """Bir xil student_code ikki marta qo'shilsa xato."""
        # pyrefly: ignore [missing-import]
        from sqlalchemy.exc import IntegrityError

        s1 = Student(full_name="A", kana_name="A", student_code="DUP001", email="a@t.com")
        s2 = Student(full_name="B", kana_name="B", student_code="DUP001", email="b@t.com")
        test_db.add(s1)
        test_db.commit()
        test_db.add(s2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_student_email_unique_constraint(self, test_db):
        """Bir xil email ikki marta qo'shilsa xato."""
        # pyrefly: ignore [missing-import]
        from sqlalchemy.exc import IntegrityError

        s1 = Student(full_name="A", kana_name="A", student_code="S001", email="dup@t.com")
        s2 = Student(full_name="B", kana_name="B", student_code="S002", email="dup@t.com")
        test_db.add(s1)
        test_db.commit()
        test_db.add(s2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_student_optional_fields_nullable(self, test_db):
        """avatar_url, semester, skill_rank, work_status — NULL bo'lishi mumkin."""
        student = Student(
            full_name="Minimal",
            kana_name="ミニマル",
            student_code="MIN001",
            email="min@test.com",
        )
        test_db.add(student)
        test_db.commit()
        test_db.refresh(student)

        assert student.avatar_url is None
        assert student.semester is None
        assert student.skill_rank is None


class TestProjectModel:
    """Project modeli."""

    def test_project_table_name(self):
        assert Project.__tablename__ == "projects"

    def test_project_status_enum_values(self):
        values = {s.value for s in ProjectStatus}
        assert values == {"done", "active", "planned", "cancelled"}

    def test_project_category_enum_values(self):
        values = {c.value for c in ProjectCategory}
        assert values == {"it", "video", "light_work", "cowork", "trial"}

    def test_project_create_and_read(self, test_db, admin_user):
        """Project DB'ga yoziladi va o'qiladi."""
        project = Project(
            name="Test Loyiha",
            overview="Loyiha tavsifi",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.ACTIVE,
            category=ProjectCategory.IT,
            created_by=admin_user.id,
        )
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)

        fetched = test_db.query(Project).filter(Project.name == "Test Loyiha").first()
        assert fetched is not None
        assert fetched.status == ProjectStatus.ACTIVE
        assert fetched.category == ProjectCategory.IT
        assert fetched.end_date == date(2026, 12, 31)

    def test_project_default_status_is_planned(self, test_db, admin_user):
        project = Project(
            name="Yangi Loyiha",
            start_date=date(2026, 1, 1),
            category=ProjectCategory.IT,
            created_by=admin_user.id,
        )
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)
        assert project.status == ProjectStatus.PLANNED


class TestProjectMemberModel:
    """ProjectMember bog'lovchi jadvali va unikal partial index."""

    def test_project_member_table_name(self):
        assert ProjectMember.__tablename__ == "project_members"

    def test_project_member_columns_exist(self):
        cols = {c.name for c in ProjectMember.__table__.columns}
        assert {"id", "project_id", "student_id", "is_leader",
                "joined_at", "left_at"}.issubset(cols)

    def test_project_member_create(self, test_db, admin_user, sample_student, sample_project):
        """Talaba loyihaga qo'shiladi."""
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
            is_leader=True,
        )
        test_db.add(pm)
        test_db.commit()
        test_db.refresh(pm)

        assert pm.id is not None
        assert pm.is_leader is True
        assert pm.left_at is None
        assert isinstance(pm.joined_at, datetime)

    def test_project_member_left_at_can_be_set(self, test_db, sample_student, sample_project):
        """left_at ni belgilash loyihadan chiqishni anglatadi."""
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
        )
        test_db.add(pm)
        test_db.commit()

        pm.left_at = datetime.utcnow()
        test_db.commit()
        test_db.refresh(pm)

        assert pm.left_at is not None


class TestProjectHistoryModel:
    """ProjectHistory log jadvali."""

    def test_project_history_table_name(self):
        assert ProjectHistory.__tablename__ == "project_history"

    def test_project_history_columns_exist(self):
        cols = {c.name for c in ProjectHistory.__table__.columns}
        assert {"id", "project_id", "changed_by", "change_type",
                "description", "created_at"}.issubset(cols)

    def test_project_history_create(self, test_db, admin_user, sample_project):
        """Loyiha o'zgarishi log sifatida yoziladi."""
        log = ProjectHistory(
            project_id=sample_project.id,
            changed_by=admin_user.id,
            change_type="status_changed",
            description="active → done",
        )
        test_db.add(log)
        test_db.commit()
        test_db.refresh(log)

        assert log.id is not None
        assert log.change_type == "status_changed"
        assert isinstance(log.created_at, datetime)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RELATIONSHIPS (BOG'LANISHLAR) TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestRelationships:

    def test_project_creator_relationship(self, test_db, admin_user, sample_project):
        """Project.creator → User bo'lishi kerak."""
        test_db.refresh(sample_project)
        assert sample_project.creator is not None
        assert sample_project.creator.id == admin_user.id

    def test_project_members_relationship(self, test_db, sample_student, sample_project):
        """Project.members → ProjectMember ro'yxati."""
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
        )
        test_db.add(pm)
        test_db.commit()
        test_db.refresh(sample_project)

        assert len(sample_project.members) == 1
        assert sample_project.members[0].student_id == sample_student.id

    def test_student_project_memberships_relationship(
        self, test_db, sample_student, sample_project
    ):
        """Student.project_memberships → ProjectMember ro'yxati."""
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
        )
        test_db.add(pm)
        test_db.commit()
        test_db.refresh(sample_student)

        assert len(sample_student.project_memberships) == 1

    def test_project_leader_relationship(self, test_db, admin_user, sample_student):
        """Project.leader → Student bo'lishi kerak."""
        project = Project(
            name="Leader Test",
            start_date=date(2026, 1, 1),
            status=ProjectStatus.ACTIVE,
            category=ProjectCategory.IT,
            created_by=admin_user.id,
            leader_student_id=sample_student.id,
        )
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)

        assert project.leader is not None
        assert project.leader.id == sample_student.id

    def test_student_concurrent_projects_count(self, test_db, sample_student, sample_project):
        """Student.concurrent_projects_count — faol loyihalar soni."""
        # Hech qanday membership yo'q
        test_db.refresh(sample_student)
        assert sample_student.concurrent_projects_count == 0

        # Faol membership qo'shamiz
        pm = ProjectMember(project_id=sample_project.id, student_id=sample_student.id)
        test_db.add(pm)
        test_db.commit()
        test_db.refresh(sample_student)
        assert sample_student.concurrent_projects_count == 1

        # left_at belgilanadi — faol emas
        pm.left_at = datetime.utcnow()
        test_db.commit()
        test_db.refresh(sample_student)
        assert sample_student.concurrent_projects_count == 0

    def test_project_cascade_delete_members(self, test_db, sample_student, sample_project):
        """Project o'chirilganda ProjectMember ham o'chadi."""
        pm = ProjectMember(project_id=sample_project.id, student_id=sample_student.id)
        test_db.add(pm)
        test_db.commit()
        pm_id = pm.id

        test_db.delete(sample_project)
        test_db.commit()

        remaining = test_db.query(ProjectMember).filter(ProjectMember.id == pm_id).first()
        assert remaining is None

    def test_project_cascade_delete_history(self, test_db, admin_user, sample_project):
        """Project o'chirilganda ProjectHistory ham o'chadi."""
        log = ProjectHistory(
            project_id=sample_project.id,
            changed_by=admin_user.id,
            change_type="info_updated",
        )
        test_db.add(log)
        test_db.commit()
        log_id = log.id

        test_db.delete(sample_project)
        test_db.commit()

        remaining = test_db.query(ProjectHistory).filter(
            ProjectHistory.id == log_id
        ).first()
        assert remaining is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MODELLARGA IMPORT TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelsImport:
    """Barcha modellar to'g'ri import qilinadi."""

    def test_all_models_importable(self):
        from src.models import (  # noqa: F401
            Base, User, Student, Project, ProjectMember, ProjectHistory,
        )
        assert True

    def test_all_models_in_metadata(self):
        """Barcha jadvallar Base.metadata da ro'yxatdan o'tgan."""
        from src.models.base import Base
        table_names = set(Base.metadata.tables.keys())
        assert {"users", "students", "projects",
                "project_members", "project_history"}.issubset(table_names)
