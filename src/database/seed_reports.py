import calendar
import os
import sys
from datetime import date, datetime, time, timedelta

# Root papkani PYTHONPATHga qo'shish
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.models.student import Student, SemesterEnum, SkillRank, WorkStatus
from src.models.user import User, UserRole
from src.models.work_report import DailyReport, MonthlyReport, ReportStatus

DESCRIPTIONS = [
    "資料の準備と整理",
    "動画素材の編集",
    "利用者との打ち合わせ",
    "報告書と書類の管理",
    "プロジェクトのテスト実施",
    "ウェブサイトの更新",
    "データベースの入力",
    "潮流の分析と調査",
]

# Har bir studentga oylar bo'yicha turli status beriladi
STATUS_CYCLE = [
    ReportStatus.SUBMITTED,
    ReportStatus.APPROVED,
    ReportStatus.REJECTED,
    ReportStatus.DRAFT,
]

DEMO_STUDENTS = [
    {"full_name": "Sato Taro", "kana_name": "サトウ タロウ", "student_code": "20260001"},
    {"full_name": "Tanaka Hanako", "kana_name": "タナカ ハナコ", "student_code": "20260002"},
    {"full_name": "Suzuki Kenji", "kana_name": "スズキ ケンジ", "student_code": "20260003"},
    {"full_name": "Xusniddin Alimov", "kana_name": "フスニディン アリモフ", "student_code": "20260011"},
    {"full_name": "Dilshod Karimov", "kana_name": "ディルショド カリモフ", "student_code": "20260012"},
]


def ensure_students(db: Session, minimum: int = 5) -> list:
    """Jadvalda kamida `minimum` ta talaba bo'lishini ta'minlaydi."""
    students = db.query(Student).order_by(Student.full_name.asc()).all()
    if len(students) >= minimum:
        return students

    print(f"Talabalar soni {len(students)} — demo talabalar qo'shilmoqda...")
    for index, info in enumerate(DEMO_STUDENTS):
        if db.query(Student).filter(Student.student_code == info["student_code"]).first():
            continue
        student = Student(
            full_name=info["full_name"],
            kana_name=info["kana_name"],
            student_code=info["student_code"],
            email=f"{info['student_code']}@example.com",
            avatar_url=f"/images/avatar-{(index % 4) + 1}.png",
            semester=SemesterEnum.SEMESTER_1,
            skill_rank=SkillRank.A,
            work_status=WorkStatus.ACTIVE,
            grad_year_month=date(2027, 3, 31),
        )
        db.add(student)
    db.commit()
    return db.query(Student).order_by(Student.full_name.asc()).all()


def build_days(year: int, month: int, offset: int) -> list:
    """Oyning kunlari: dam olish kuni yakshanba, boshqalarda ish vaqti."""
    last_day = calendar.monthrange(year, month)[1]
    start_hour = 9 if offset % 2 == 0 else 13
    finish_hour = start_hour + 8
    days = []
    for day_number in range(1, last_day + 1):
        work_date = date(year, month, day_number)
        is_day_off = work_date.weekday() == 6
        if is_day_off:
            days.append({"work_date": work_date, "is_day_off": True})
            continue
        days.append(
            {
                "work_date": work_date,
                "is_day_off": False,
                "start_time": time(start_hour, 0),
                "finish_time": time(finish_hour % 24, 0),
                "description": DESCRIPTIONS[(work_date.toordinal() + offset) % len(DESCRIPTIONS)],
            }
        )
    return days


def previous_period(today: date) -> tuple[int, int]:
    first = today.replace(day=1)
    last_month_end = first - timedelta(days=1)
    return last_month_end.year, last_month_end.month


def seed_reports():
    db: Session = SessionLocal()
    try:
        today = date.today()
        periods = [previous_period(today), (today.year, today.month)]

        print("Eski demo hisobotlarni tozalash...")
        db.query(DailyReport).delete()
        db.query(MonthlyReport).delete()
        db.commit()

        students = ensure_students(db)
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        print(f"{len(students)} ta talaba topildi.")

        total = 0
        for period_index, (year, month) in enumerate(periods):
            for student_index, student in enumerate(students):
                status = (
                    ReportStatus.APPROVED
                    if period_index == 0
                    else STATUS_CYCLE[(student_index + period_index) % len(STATUS_CYCLE)]
                )
                report = MonthlyReport(
                    student_id=student.id,
                    year=year,
                    month=month,
                    status=status,
                    week_1="第1週は予定どおりに完了しました。",
                    week_2="第2週は担当業務を期限内に完了しました。",
                    week_3="第3週はチームとの調整業務を行いました。",
                    week_4="第4週は結果を分析しました。",
                    week_5="第5週に最終報告書を作成しました。",
                )
                if status in (ReportStatus.SUBMITTED, ReportStatus.APPROVED, ReportStatus.REJECTED):
                    report.submitted_at = datetime(year, month, min(calendar.monthrange(year, month)[1], 5), 10, 0)
                if status in (ReportStatus.APPROVED, ReportStatus.REJECTED):
                    report.reviewed_at = datetime(year, month, min(calendar.monthrange(year, month)[1], 10), 15, 0)
                    report.reviewed_by = admin.id if admin else None
                if status is ReportStatus.APPROVED:
                    report.stipend_amount = 160000 + student_index * 8000
                if status is ReportStatus.REJECTED:
                    report.review_note = "勤務時間と備考の内容を再確認してください。"

                db.add(report)
                db.flush()

                for entry in build_days(year, month, student_index + period_index):
                    db.add(
                        DailyReport(
                            monthly_report_id=report.id,
                            work_date=entry["work_date"],
                            is_day_off=entry["is_day_off"],
                            start_time=entry.get("start_time"),
                            finish_time=entry.get("finish_time"),
                            description=entry.get("description"),
                        )
                    )
                total += 1
            db.commit()
            print(f"{year}-{month:02d}: {len(students)} ta hisobot yaratildi.")

        print(f"--- JAMI {total} TA HISOBOT YARATILDI! ---")
        print("Admin hisobotlar sahifasida Excel yuklab olish tugmasi faol bo'ladi.")

    except Exception as e:
        db.rollback()
        print(f"Seed jarayonida xatolik: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_reports()