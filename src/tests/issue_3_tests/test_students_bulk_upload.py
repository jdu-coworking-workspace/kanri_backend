"""Issue 03 (qo'shimcha): Talabalarni ommaviy import qilish.

Testlar:
1. Template download (xlsx/csv) va huquqlar
2. CSV upload — muvaffaqiyatli, xatolar, skip_invalid
3. XLSX upload — muvaffaqiyatli, qator raqamlari
4. Fayl validatsiyasi — extension, bo'sh fayl, header, limit
5. Yaratilgan studentlar uchun user/avatar tekshiruvi
"""
from io import BytesIO

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from openpyxl import Workbook

from src.models import Student, User
from src.services.student_service import ANONYMOUS_AVATAR_URL
from src.utils.student_import import MAX_ROWS

HEADER = "full_name,kana_name,student_code,email,grad_year_month,semester,skill_rank,work_status"


def csv_bytes(*lines: str) -> bytes:
    return ("\n".join((HEADER, *lines)) + "\n").encode("utf-8")


def xlsx_bytes(rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADER.split(","))
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload(client, cookie, content: bytes, filename: str, skip_invalid: bool = False):
    client.cookies.set("access_token", cookie)
    return client.post(
        "/api/v1/students/bulk/upload",
        files={
            "file": (
                filename,
                content,
                "text/csv" if filename.endswith(".csv") else
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"skip_invalid": str(skip_invalid).lower()},
    )


VALID_ROW = "Ali Valiyev,アリ・バリエフ,UZ240001,ali@example.com,2026-06-01,1-semestr,C,active"
SECOND_ROW = "Vali Karimov,バリ・カリモフ,UZ240002,vali@example.com,,2-semestr,B,intern"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TEMPLATE DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBulkTemplateDownload:

    def test_download_xlsx_template(self, client, admin_cookie):
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students/bulk/template/xlsx")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "students.xlsx" in resp.headers["content-disposition"]
        assert resp.content[:2] == b"PK"

    def test_download_csv_template(self, client, admin_cookie):
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students/bulk/template/csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "students.csv" in resp.headers["content-disposition"]
        text = resp.content.decode("utf-8-sig")
        assert text.splitlines()[0] == HEADER

    def test_template_requires_auth(self, client):
        assert client.get("/api/v1/students/bulk/template/xlsx").status_code == 401

    def test_template_forbidden_for_staff(self, client, staff_cookie):
        client.cookies.set("access_token", staff_cookie)
        assert client.get("/api/v1/students/bulk/template/xlsx").status_code == 403

    def test_template_unknown_format_returns_404(self, client, admin_cookie):
        client.cookies.set("access_token", admin_cookie)
        assert client.get("/api/v1/students/bulk/template/pdf").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CSV UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBulkCsvUpload:

    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/v1/students/bulk/upload",
            files={"file": ("students.csv", csv_bytes(VALID_ROW), "text/csv")},
        )
        assert resp.status_code == 401

    def test_upload_forbidden_for_staff(self, client, staff_cookie):
        resp = upload(client, staff_cookie, csv_bytes(VALID_ROW), "students.csv")
        assert resp.status_code == 403

    def test_upload_creates_students(self, client, admin_cookie, test_db):
        resp = upload(client, admin_cookie, csv_bytes(VALID_ROW, SECOND_ROW), "students.csv")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["total"] == 2
        assert body["created_count"] == 2
        assert body["failed_count"] == 0
        assert [item["row"] for item in body["created"]] == [2, 3]
        assert body["created"][0]["student_code"] == "UZ240001"

        students = test_db.query(Student).order_by(Student.student_code).all()
        assert len(students) == 2
        assert students[0].semester.value == "1-semestr"
        assert students[0].skill_rank.value == "C"
        assert students[0].work_status.value == "active"
        assert students[0].grad_year_month.isoformat() == "2026-06-01"
        assert students[0].avatar_url == ANONYMOUS_AVATAR_URL

    def test_upload_creates_login_users(self, client, admin_cookie, test_db):
        resp = upload(client, admin_cookie, csv_bytes(VALID_ROW), "students.csv")
        assert resp.status_code == 201, resp.text

        student = test_db.query(Student).filter(Student.student_code == "UZ240001").one()
        user = test_db.query(User).filter(User.id == student.user_id).one()
        assert user.email == "ali@example.com"
        assert user.role.value == "student"
        assert user.password_hash

    def test_upload_accepts_bom_and_blank_lines(self, client, admin_cookie):
        content = ("\ufeff" + HEADER + "\n\n" + VALID_ROW + "\n\n").encode("utf-8")
        resp = upload(client, admin_cookie, content, "students.csv")
        assert resp.status_code == 201, resp.text
        assert resp.json()["created_count"] == 1

    def test_upload_normalizes_slash_dates_and_semester(self, client, admin_cookie, test_db):
        row = "Ali Valiyev,アリ,UZ240010,ali10@example.com,2026/06/01,4, a ,Active"
        resp = upload(client, admin_cookie, csv_bytes(row), "students.csv")
        assert resp.status_code == 201, resp.text
        student = test_db.query(Student).filter(Student.student_code == "UZ240010").one()
        assert student.grad_year_month.isoformat() == "2026-06-01"
        assert student.semester.value == "4-semestr"
        assert student.skill_rank.value == "A"
        assert student.work_status.value == "active"

    def test_upload_invalid_row_blocks_everything(self, client, admin_cookie, test_db):
        bad = "Ali Valiyev,アリ,UZ240001,not-an-email,,,," 
        resp = upload(client, admin_cookie, csv_bytes(VALID_ROW, bad), "students.csv")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["code"] == "BULK_VALIDATION_FAILED"
        assert detail["errors"][0]["row"] == 3
        assert test_db.query(Student).count() == 0

    def test_upload_skip_invalid_creates_valid_rows(self, client, admin_cookie, test_db):
        bad = "Ali Valiyev,アリ,UZ240001,not-an-email,,,," 
        resp = upload(
            client, admin_cookie, csv_bytes(VALID_ROW, bad), "students.csv", skip_invalid=True
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["created_count"] == 1
        assert body["failed_count"] == 1
        assert body["errors"][0]["row"] == 3
        assert test_db.query(Student).count() == 1

    def test_upload_detects_duplicate_inside_file(self, client, admin_cookie, test_db):
        resp = upload(client, admin_cookie, csv_bytes(VALID_ROW, VALID_ROW), "students.csv")
        assert resp.status_code == 422
        errors = resp.json()["detail"]["errors"]
        assert errors[0]["row"] == 3
        assert any("takrorlangan" in msg for msg in errors[0]["errors"])
        assert test_db.query(Student).count() == 0

    def test_upload_detects_duplicate_in_database(
        self, client, admin_cookie, sample_student, test_db
    ):
        row = "Boshqa Ism,ベツ,UZ240001,other@example.com,,,," 
        resp = upload(client, admin_cookie, csv_bytes(row), "students.csv")
        assert resp.status_code == 422
        errors = resp.json()["detail"]["errors"]
        assert any("student_code" in msg for msg in errors[0]["errors"])

    def test_upload_detects_existing_user_email(self, client, admin_cookie, admin_user):
        row = "Boshqa Ism,ベツ,UZ240099,admin@test.com,,,," 
        resp = upload(client, admin_cookie, csv_bytes(row), "students.csv")
        assert resp.status_code == 422
        errors = resp.json()["detail"]["errors"]
        assert any("foydalanuvchi" in msg for msg in errors[0]["errors"])

    def test_upload_all_rows_invalid_returns_nothing_to_create(
        self, client, admin_cookie
    ):
        bad = "Ali Valiyev,アリ,UZ240001,not-an-email,,,," 
        resp = upload(client, admin_cookie, csv_bytes(bad), "students.csv", skip_invalid=True)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "BULK_NOTHING_TO_CREATE"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. XLSX UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestBulkXlsxUpload:

    def test_upload_xlsx_creates_students(self, client, admin_cookie, test_db):
        content = xlsx_bytes(
            [
                ["Ali Valiyev", "アリ・バリエフ", "UZ240001", "ali@example.com", "2026-06-01", "1-semestr", "C", "active"],
                ["Vali Karimov", "バリ", "UZ240002", "vali@example.com", None, "2-semestr", "B", "intern"],
            ]
        )
        resp = upload(client, admin_cookie, content, "students.xlsx")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["created_count"] == 2
        assert [item["row"] for item in body["created"]] == [2, 3]
        assert test_db.query(Student).count() == 2

    def test_upload_xlsx_reports_excel_row_numbers(self, client, admin_cookie):
        content = xlsx_bytes(
            [
                ["Ali Valiyev", "アリ", "UZ240001", "ali@example.com", None, None, None, None],
                ["", "", "", "", None, None, None, None],
                ["Vali Karimov", "バリ", "UZ240002", "bad-email", None, None, None, None],
            ]
        )
        resp = upload(client, admin_cookie, content, "students.xlsx")
        assert resp.status_code == 422
        errors = resp.json()["detail"]["errors"]
        assert errors[0]["row"] == 4

    def test_upload_xlsx_accepts_real_date_cells(self, client, admin_cookie, test_db):
        from datetime import date

        content = xlsx_bytes(
            [["Ali Valiyev", "アリ", "UZ240001", "ali@example.com", date(2026, 6, 1), "1-semestr", "C", "active"]]
        )
        resp = upload(client, admin_cookie, content, "students.xlsx")
        assert resp.status_code == 201, resp.text
        student = test_db.query(Student).filter(Student.student_code == "UZ240001").one()
        assert student.grad_year_month.isoformat() == "2026-06-01"

    def test_upload_xlsx_converts_numeric_student_codes_to_strings(
        self, client, admin_cookie, test_db
    ):
        content = xlsx_bytes(
            [[
                "Ali Valiyev",
                "アリ",
                806223.0,
                "ali806223@example.com",
                None,
                None,
                None,
                None,
            ]]
        )
        resp = upload(client, admin_cookie, content, "students.xlsx")
        assert resp.status_code == 201, resp.text
        student = test_db.query(Student).filter(Student.student_code == "806223").one()
        assert student.student_code == "806223"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FAYL VALIDATSIYASI
# ═══════════════════════════════════════════════════════════════════════════════

class TestBulkFileValidation:

    def test_rejects_unsupported_extension(self, client, admin_cookie):
        resp = upload(client, admin_cookie, b"data", "students.txt")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"

    def test_rejects_empty_file(self, client, admin_cookie):
        resp = upload(client, admin_cookie, b"", "students.csv")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "EMPTY_FILE"

    def test_rejects_header_only_file(self, client, admin_cookie):
        resp = upload(client, admin_cookie, (HEADER + "\n").encode(), "students.csv")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "EMPTY_FILE"

    def test_rejects_missing_required_columns(self, client, admin_cookie):
        content = "full_name,student_code\nAli,UZ240001\n".encode()
        resp = upload(client, admin_cookie, content, "students.csv")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["code"] == "MISSING_COLUMNS"
        assert any("kana_name" in msg for msg in detail["errors"][0]["errors"])

    def test_rejects_unknown_columns(self, client, admin_cookie):
        content = (HEADER + ",favorite_color\n" + VALID_ROW + ",blue\n").encode()
        resp = upload(client, admin_cookie, content, "students.csv")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNKNOWN_COLUMNS"

    def test_rejects_too_many_rows(self, client, admin_cookie):
        rows = [
            f"Ali {i},アリ,UZ25{i:04d},ali{i}@example.com,,,," 
            for i in range(MAX_ROWS + 1)
        ]
        resp = upload(client, admin_cookie, csv_bytes(*rows), "students.csv")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "TOO_MANY_ROWS"

    def test_rejects_corrupted_xlsx(self, client, admin_cookie):
        resp = upload(client, admin_cookie, b"not-a-zip", "students.xlsx")
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_FILE"

    def test_rejects_oversized_file(self, client, admin_cookie):
        from src.utils.student_import import MAX_FILE_SIZE_BYTES

        content = b"a" * (MAX_FILE_SIZE_BYTES + 1)
        resp = upload(client, admin_cookie, content, "students.csv")
        assert resp.status_code == 413
        assert resp.json()["detail"]["code"] == "FILE_TOO_LARGE"

    def test_accepts_japanese_headers(self, client, admin_cookie, test_db):
        content = (
            "氏名,フリガナ,学籍番号,メールアドレス\n"
            "Ali Valiyev,アリ,UZ240001,ali@example.com\n"
        ).encode()
        resp = upload(client, admin_cookie, content, "students.csv")
        assert resp.status_code == 201, resp.text
        assert test_db.query(Student).count() == 1
