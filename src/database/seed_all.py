import os
import sys
from datetime import date, datetime

# Root papkani PYTHONPATHga qo'shish
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.models.user import User, UserRole
from src.models.student import Student, SemesterEnum, SkillRank, WorkStatus
from src.models.project import Project, ProjectStatus, ProjectCategory
from src.models.project_member import ProjectMember
from src.utils.security import get_password_hash

def seed_all():
    db: Session = SessionLocal()
    try:
        print("Mavjud talabalar va loyihalar ma'lumotlarini o'chirish...")
        db.query(ProjectMember).delete()
        db.query(Project).delete()
        db.query(Student).delete()
        db.commit()

        # 1. Users (Admin va Staff) yaratish
        print("Xodimlarni (Users) yaratish...")
        users_to_create = [
            {"email": "adminexample1@gmail.com", "full_name": "Admin Example", "role": UserRole.ADMIN},
            {"email": "staffexample1@gmail.com", "full_name": "Staff Helper 1", "role": UserRole.STAFF},
            {"email": "staffexample2@gmail.com", "full_name": "Staff Helper 2", "role": UserRole.STAFF},
        ]
        
        password = "password123"
        hashed_password = get_password_hash(password)
        created_users = []

        for u_data in users_to_create:
            existing_user = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing_user:
                new_user = User(
                    email=u_data["email"],
                    password_hash=hashed_password,
                    full_name=u_data["full_name"],
                    role=u_data["role"]
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                created_users.append(new_user)
                print(f"Yozildi: {new_user.email}")
            else:
                created_users.append(existing_user)
                print(f"Mavjud: {existing_user.email}")

        admin_user = next(u for u in created_users if u.role == UserRole.ADMIN)

        # 2. 20 ta talaba (Students) yaratish
        print("20 ta talabani (Students) yaratish...")
        students_data = [
            {"full_name": "Sato Taro", "kana_name": "サトウ タロウ", "student_code": "20260001", "email": "taro.sato@example.com", "semester": SemesterEnum.SEMESTER_1, "skill_rank": SkillRank.A},
            {"full_name": "Tanaka Hanako", "kana_name": "タナカ ハナコ", "student_code": "20260002", "email": "hanako.tanaka@example.com", "semester": SemesterEnum.SEMESTER_2, "skill_rank": SkillRank.B},
            {"full_name": "Suzuki Kenji", "kana_name": "スズキ ケンジ", "student_code": "20260003", "email": "kenji.suzuki@example.com", "semester": SemesterEnum.SEMESTER_3, "skill_rank": SkillRank.S},
            {"full_name": "Ichikawa Yui", "kana_name": "イチカワ ユイ", "student_code": "20260004", "email": "yui.ichikawa@example.com", "semester": SemesterEnum.SEMESTER_4, "skill_rank": SkillRank.C},
            {"full_name": "Watanabe Hiroto", "kana_name": "ワタナベ ヒロト", "student_code": "20260005", "email": "hiroto.watanabe@example.com", "semester": SemesterEnum.SEMESTER_5, "skill_rank": SkillRank.A},
            {"full_name": "Takahashi Sora", "kana_name": "タカハシ ソラ", "student_code": "20260006", "email": "sora.takahashi@example.com", "semester": SemesterEnum.SEMESTER_6, "skill_rank": SkillRank.B},
            {"full_name": "Nakamura Aoi", "kana_name": "ナカムラ アオイ", "student_code": "20260007", "email": "aoi.nakamura@example.com", "semester": SemesterEnum.SEMESTER_1, "skill_rank": SkillRank.B},
            {"full_name": "Kobayashi Ren", "kana_name": "コバヤシ レン", "student_code": "20260008", "email": "ren.kobayashi@example.com", "semester": SemesterEnum.SEMESTER_2, "skill_rank": SkillRank.A},
            {"full_name": "Kato Himari", "kana_name": "カトウ ヒマリ", "student_code": "20260009", "email": "himari.kato@example.com", "semester": SemesterEnum.SEMESTER_3, "skill_rank": SkillRank.C},
            {"full_name": "Yoshida Yuto", "kana_name": "ヨシダ ユウト", "student_code": "20260010", "email": "yuto.yoshida@example.com", "semester": SemesterEnum.SEMESTER_4, "skill_rank": SkillRank.S},
            {"full_name": "Xusniddin Alimov", "kana_name": "フスニディン アリモフ", "student_code": "20260011", "email": "xusniddin@example.com", "semester": SemesterEnum.SEMESTER_8, "skill_rank": SkillRank.A},
            {"full_name": "Dilshod Karimov", "kana_name": "ディルショド カリモフ", "student_code": "20260012", "email": "dilshod@example.com", "semester": SemesterEnum.SEMESTER_6, "skill_rank": SkillRank.B},
            {"full_name": "Nodira Zokirova", "kana_name": "ノディラ ゾキロワ", "student_code": "20260013", "email": "nodira@example.com", "semester": SemesterEnum.SEMESTER_5, "skill_rank": SkillRank.S},
            {"full_name": "Shamil Rustamov", "kana_name": "シャミル ルスタモフ", "student_code": "20260014", "email": "shamil@example.com", "semester": SemesterEnum.SEMESTER_4, "skill_rank": SkillRank.B},
            {"full_name": "Inoue Sakura", "kana_name": "イノウエ サクラ", "student_code": "20260015", "email": "sakura.inoue@example.com", "semester": SemesterEnum.SEMESTER_3, "skill_rank": SkillRank.C},
            {"full_name": "Hayashi Kazuki", "kana_name": "ハヤシ カズキ", "student_code": "20260016", "email": "kazuki.hayashi@example.com", "semester": SemesterEnum.SEMESTER_2, "skill_rank": SkillRank.A},
            {"full_name": "Saito Mei", "kana_name": "サイトウ メイ", "student_code": "20260017", "email": "mei.saito@example.com", "semester": SemesterEnum.SEMESTER_1, "skill_rank": SkillRank.B},
            {"full_name": "Shimizu Taiga", "kana_name": "シミズ タイガ", "student_code": "20260018", "email": "taiga.shimizu@example.com", "semester": SemesterEnum.SEMESTER_2, "skill_rank": SkillRank.A},
            {"full_name": "Abe Nanami", "kana_name": "アベ ナナミ", "student_code": "20260019", "email": "nanami.abe@example.com", "semester": SemesterEnum.SEMESTER_3, "skill_rank": SkillRank.B},
            {"full_name": "Morita Kaito", "kana_name": "モリタ カイト", "student_code": "20260020", "email": "kaito.morita@example.com", "semester": SemesterEnum.SEMESTER_4, "skill_rank": SkillRank.S},
        ]

        created_students = []
        for idx, s_info in enumerate(students_data):
            avatar_num = (idx % 4) + 1
            new_student = Student(
                full_name=s_info["full_name"],
                kana_name=s_info["kana_name"],
                student_code=s_info["student_code"],
                email=s_info["email"],
                avatar_url=f"/images/avatar-{avatar_num}.png",
                semester=s_info["semester"],
                skill_rank=s_info["skill_rank"],
                work_status=WorkStatus.ACTIVE,
                point_1=10 + (idx * 2),
                point_2=15 + (idx * 3),
                point_3=20 + idx,
                grad_year_month=date(2027, 3, 31)
            )
            db.add(new_student)
            created_students.append(new_student)
        
        db.commit()
        for s in created_students:
            db.refresh(s)
        print("20 ta talaba muvaffaqiyatli yaratildi.")

        # 3. 5 ta loyiha (Projects) yaratish
        print("5 ta loyihani (Projects) yaratish...")
        projects_data = [
            {"name": "Kanri Platform Dev", "overview": "Tizimni to'liq boshqarish va integratsiya loyihasi.", "start_date": date(2026, 1, 10), "end_date": date(2026, 12, 31), "status": ProjectStatus.ACTIVE, "category": ProjectCategory.IT},
            {"name": "Uzbek Promo Video", "overview": "Uzbekistan madaniyati bo'yicha chiroyli visual rolik.", "start_date": date(2026, 2, 15), "end_date": date(2026, 6, 30), "status": ProjectStatus.ACTIVE, "category": ProjectCategory.VIDEO},
            {"name": "IT Hub Network Setup", "overview": "Lokal tarmoq infrastrukturasi va xavfsizligini sozlash.", "start_date": date(2026, 3, 1), "end_date": date(2026, 5, 15), "status": ProjectStatus.PLANNED, "category": ProjectCategory.IT},
            {"name": "Office Digitalization Trial", "overview": "Ofisni raqamlashtirish bo'yicha sinov.", "start_date": date(2026, 1, 5), "end_date": date(2026, 2, 28), "status": ProjectStatus.DONE, "category": ProjectCategory.TRIAL},
            {"name": "SMM Marketing Campaign", "overview": "Brendni ijtimoiy tarmoqlarda targ'ib etish ishi.", "start_date": date(2026, 4, 1), "end_date": date(2026, 8, 31), "status": ProjectStatus.PLANNED, "category": ProjectCategory.LIGHT_WORK},
        ]

        created_projects = []
        for p_info in projects_data:
            new_project = Project(
                name=p_info["name"],
                overview=p_info["overview"],
                start_date=p_info["start_date"],
                end_date=p_info["end_date"],
                status=p_info["status"],
                category=p_info["category"],
                created_by=admin_user.id
            )
            db.add(new_project)
            created_projects.append(new_project)
        
        db.commit()
        for p in created_projects:
            db.refresh(p)
        print("5 ta loyiha yaratildi.")

        # 4. Loyiha a'zolarini biriktirish
        print("Loyiha a'zolarini (Project Members) shakllantirish...")
        # Project 0 (Kanri Platform Dev) -> 4 members, student 0 is leader
        memberships = [
            # Project 0: Kanri Platform Dev
            ProjectMember(project_id=created_projects[0].id, student_id=created_students[0].id, is_leader=True),
            ProjectMember(project_id=created_projects[0].id, student_id=created_students[1].id, is_leader=False),
            ProjectMember(project_id=created_projects[0].id, student_id=created_students[2].id, is_leader=False),
            ProjectMember(project_id=created_projects[0].id, student_id=created_students[3].id, is_leader=False),

            # Project 1: Uzbek Promo Video
            ProjectMember(project_id=created_projects[1].id, student_id=created_students[4].id, is_leader=True),
            ProjectMember(project_id=created_projects[1].id, student_id=created_students[5].id, is_leader=False),
            ProjectMember(project_id=created_projects[1].id, student_id=created_students[6].id, is_leader=False),

            # Project 2: IT Hub Network Setup
            ProjectMember(project_id=created_projects[2].id, student_id=created_students[7].id, is_leader=True),
            ProjectMember(project_id=created_projects[2].id, student_id=created_students[8].id, is_leader=False),
            ProjectMember(project_id=created_projects[2].id, student_id=created_students[18].id, is_leader=False),
            ProjectMember(project_id=created_projects[2].id, student_id=created_students[19].id, is_leader=False),

            # Project 3: Office Digitalization Trial
            ProjectMember(project_id=created_projects[3].id, student_id=created_students[9].id, is_leader=True),
            ProjectMember(project_id=created_projects[3].id, student_id=created_students[10].id, is_leader=False),
        ]

        for m in memberships:
            db.add(m)
        db.commit()

        # Update Project leader_student_id reference to match memberships leaders
        created_projects[0].leader_student_id = created_students[0].id
        created_projects[1].leader_student_id = created_students[4].id
        created_projects[2].leader_student_id = created_students[7].id
        created_projects[3].leader_student_id = created_students[9].id
        db.commit()

        print("A'zolar va loyiha rahbarlari bog'landi.")
        print("--- BARCHASI MUVAFFAQIYATLI SEED QILINDI! ---")

    except Exception as e:
        db.rollback()
        print(f"Seed jarayonida xatolik: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
