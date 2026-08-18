"""
Issue 03: Talabalar (Students) CRUD va Filtratsiya API

Testlar:
1. GET /students — ro'yxat, pagination, qidiruv, auth
2. GET /students/{id} — batafsil + history, auth
3. GET /students/{id}/history — faqat tarixi
4. POST /students — yaratish, unikal tekshiruv
5. PUT /students/{id} — tahrirlash
6. DELETE /students/{id} — o'chirish
7. POST /students/{id}/copy — nusxalash
8. Huquqlar: GET → get_current_user, POST/PUT/DELETE → require_editor
"""
# pyrefly: ignore [missing-import]
import pytest
from src.models import Student, ProjectMember


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

VALID_STUDENT = {
    "full_name": "Karimova Nilufar",
    "kana_name": "カリモワ",
    "student_code": "UZ240001",
    "email": "nilufar@test.com",
}


def make_student(overrides: dict = None) -> dict:
    data = VALID_STUDENT.copy()
    if overrides:
        data.update(overrides)
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GET /students — RO'YXAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStudentsList:

    def test_get_students_requires_auth(self, client):
        """Cookie yo'q → 401."""
        resp = client.get("/api/v1/students")
        assert resp.status_code == 401

    def test_get_students_empty_list(self, client, admin_cookie):
        """DB bo'sh bo'lsa bo'sh ro'yxat qaytaradi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_get_students_returns_correct_format(self, client, admin_cookie, sample_student):
        """Javob formati: success, data, meta (total, page, limit, total_pages)."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students")
        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body
        assert "data" in body
        assert "meta" in body
        meta = body["meta"]
        assert "total" in meta
        assert "page" in meta
        assert "limit" in meta
        assert "total_pages" in meta

    def test_get_students_returns_one_student(self, client, admin_cookie, sample_student):
        """Bazada 1 ta student bo'lsa 1 ta qaytaradi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students")
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["student_code"] == "UZ240001"

    def test_get_students_search_by_full_name(self, client, admin_cookie, test_db):
        """q parametri bilan full_name bo'yicha qidirish."""
        s1 = Student(full_name="Aliyev Bobur", kana_name="ア", student_code="AL001", email="al@t.com")
        s2 = Student(full_name="Karimov Jasur", kana_name="カ", student_code="KR001", email="kr@t.com")
        test_db.add_all([s1, s2])
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students?q=Aliyev")
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["full_name"] == "Aliyev Bobur"

    def test_get_students_search_by_student_code(self, client, admin_cookie, test_db):
        """q parametri bilan student_code bo'yicha qidirish."""
        s = Student(full_name="Test", kana_name="テ", student_code="UNIQUE999", email="u999@t.com")
        test_db.add(s)
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students?q=UNIQUE999")
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["student_code"] == "UNIQUE999"

    def test_get_students_search_no_match(self, client, admin_cookie, sample_student):
        """Mos kelmaydigan qidiruv — bo'sh ro'yxat."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students?q=NOMATCH_XYZ")
        body = resp.json()
        assert body["meta"]["total"] == 0
        assert body["data"] == []

    def test_get_students_pagination_limit(self, client, admin_cookie, test_db):
        """limit parametri ishlaydi."""
        for i in range(5):
            test_db.add(Student(
                full_name=f"Student {i}", kana_name="ス",
                student_code=f"S00{i}", email=f"s{i}@t.com"
            ))
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students?limit=2&page=1")
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5
        assert body["meta"]["total_pages"] == 3

    def test_get_students_pagination_page_2(self, client, admin_cookie, test_db):
        """2-sahifa to'g'ri ishlaydi."""
        for i in range(4):
            test_db.add(Student(
                full_name=f"P{i}", kana_name="ペ",
                student_code=f"P00{i}", email=f"p{i}@t.com"
            ))
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/students?limit=2&page=2")
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["page"] == 2

    def test_get_students_viewer_can_access(self, client, staff_cookie, sample_student):
        """Viewer ham ro'yxatni ko'ra oladi."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.get("/api/v1/students")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GET /students/{id} — BATAFSIL
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStudentDetail:

    def test_get_student_requires_auth(self, client, sample_student):
        """Cookie yo'q → 401."""
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 401

    def test_get_student_success(self, client, admin_cookie, sample_student):
        """Mavjud talaba ma'lumotini qaytaradi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["student_code"] == "UZ240001"
        assert data["full_name"] == "Karimova Nilufar"

    def test_get_student_includes_history_field(self, client, admin_cookie, sample_student):
        """Javobda history maydoni bo'lishi kerak."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        data = resp.json()["data"]
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_get_student_history_empty_when_no_projects(self, client, admin_cookie, sample_student):
        """Talaba hech bir loyihada bo'lmasa history bo'sh."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        assert resp.json()["data"]["history"] == []

    def test_get_student_history_with_project(
        self, client, admin_cookie, test_db, sample_student, sample_project
    ):
        """Talaba loyihaga qo'shilgan bo'lsa history ko'rsatadi."""
        pm = ProjectMember(project_id=sample_project.id, student_id=sample_student.id, is_leader=True)
        test_db.add(pm)
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        history = resp.json()["data"]["history"]
        assert len(history) == 1
        assert history[0]["project_name"] == "Test Loyiha"
        assert history[0]["is_leader"] is True

    def test_get_student_not_found_returns_404(self, client, admin_cookie):
        """Mavjud bo'lmagan ID → 404."""
        import uuid
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_student_viewer_can_access(self, client, staff_cookie, sample_student):
        """Viewer ham ko'ra oladi."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GET /students/{id}/history — FAQAT TARIXI
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStudentHistory:

    def test_history_requires_auth(self, client, sample_student):
        resp = client.get(f"/api/v1/students/{sample_student.id}/history")
        assert resp.status_code == 401

    def test_history_empty(self, client, admin_cookie, sample_student):
        """Loyihasi bo'lmagan talabaning tarixi bo'sh."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []

    def test_history_shows_project_membership(
        self, client, admin_cookie, test_db, sample_student, sample_project
    ):
        """Talaba loyihaga qo'shilganda tarixda ko'rinadi."""
        from datetime import datetime
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
            is_leader=False,
        )
        test_db.add(pm)
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}/history")
        body = resp.json()
        assert len(body["data"]) == 1
        item = body["data"][0]
        assert str(sample_project.id) == item["project_id"]
        assert item["project_name"] == "Test Loyiha"
        assert item["is_leader"] is False
        assert item["left_at"] is None

    def test_history_shows_left_project(
        self, client, admin_cookie, test_db, sample_student, sample_project
    ):
        """Chiqib ketilgan loyiha ham tarixda ko'rinadi."""
        from datetime import datetime
        pm = ProjectMember(
            project_id=sample_project.id,
            student_id=sample_student.id,
            left_at=datetime(2026, 6, 1),
        )
        test_db.add(pm)
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{sample_student.id}/history")
        item = resp.json()["data"][0]
        assert item["left_at"] is not None

    def test_history_not_found_returns_404(self, client, admin_cookie):
        import uuid
        client.cookies.set("access_token", admin_cookie)
        resp = client.get(f"/api/v1/students/{uuid.uuid4()}/history")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 4. POST /students — YARATISH
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateStudent:

    def test_create_requires_auth(self, client):
        resp = client.post("/api/v1/students", json=make_student())
        assert resp.status_code == 401

    def test_create_requires_editor(self, client, staff_cookie):
        """Viewer yarata olmaydi → 403."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.post("/api/v1/students", json=make_student())
        assert resp.status_code == 403

    def test_create_student_success(self, client, admin_cookie):
        """Editor muvaffaqiyatli talaba yaratadi → 201."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post("/api/v1/students", json=make_student())
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["student_code"] == "UZ240001"
        assert data["full_name"] == "Karimova Nilufar"
        assert "id" in data

    def test_create_student_with_all_fields(self, client, admin_cookie):
        """Barcha maydonlar bilan yaratish."""
        client.cookies.set("access_token", admin_cookie)
        payload = make_student({
            "skill_rank": "S",
            "work_status": "active",
            "semester": "4-semestr",
            "grad_year_month": "2026-06-01",
            "point_1": 10, "point_2": 20, "point_3": 30,
        })
        resp = client.post("/api/v1/students", json=payload)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["skill_rank"] == "S"
        assert data["point_1"] == 10

    def test_create_duplicate_student_code_returns_409(self, client, admin_cookie):
        """Duplicate student_code → 409."""
        client.cookies.set("access_token", admin_cookie)
        client.post("/api/v1/students", json=make_student())
        resp = client.post("/api/v1/students", json=make_student({"email": "other@t.com"}))
        assert resp.status_code == 409

    def test_create_duplicate_email_returns_409(self, client, admin_cookie):
        """Duplicate email → 409."""
        client.cookies.set("access_token", admin_cookie)
        client.post("/api/v1/students", json=make_student())
        resp = client.post("/api/v1/students", json=make_student({"student_code": "DIFF001"}))
        assert resp.status_code == 409

    def test_create_missing_required_field_returns_422(self, client, admin_cookie):
        """full_name yo'q → 422."""
        client.cookies.set("access_token", admin_cookie)
        payload = {"kana_name": "カ", "student_code": "X001", "email": "x@t.com"}
        resp = client.post("/api/v1/students", json=payload)
        assert resp.status_code == 422

    def test_create_invalid_email_returns_422(self, client, admin_cookie):
        """Noto'g'ri email formati → 422."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post("/api/v1/students", json=make_student({"email": "notemail"}))
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PUT /students/{id} — TAHRIRLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateStudent:

    def test_update_requires_auth(self, client, sample_student):
        resp = client.put(f"/api/v1/students/{sample_student.id}", json={"full_name": "Yangi"})
        assert resp.status_code == 401

    def test_update_requires_editor(self, client, staff_cookie, sample_student):
        client.cookies.set("access_token", staff_cookie)
        resp = client.put(f"/api/v1/students/{sample_student.id}", json={"full_name": "Y"})
        assert resp.status_code == 403

    def test_update_full_name(self, client, admin_cookie, sample_student):
        """full_name yangilanadi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.put(
            f"/api/v1/students/{sample_student.id}",
            json={"full_name": "Yangilangan Ism"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Yangilangan Ism"

    def test_update_partial_fields_only(self, client, admin_cookie, sample_student):
        """Faqat bitta maydon o'zgaradi, qolganlari o'zgarmaydi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.put(
            f"/api/v1/students/{sample_student.id}",
            json={"skill_rank": "S"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["skill_rank"] == "S"
        assert data["student_code"] == "UZ240001"  # o'zgarmagan

    def test_update_duplicate_student_code_returns_409(self, client, admin_cookie, test_db):
        """Boshqa talabaning student_code'ini olishga urinish → 409."""
        s2 = Student(full_name="B", kana_name="B", student_code="TAKEN", email="b@t.com")
        test_db.add(s2)
        test_db.commit()

        client.cookies.set("access_token", admin_cookie)
        # Avval asosiy student yaratamiz
        resp = client.post("/api/v1/students", json=make_student())
        assert resp.status_code == 201
        student_id = resp.json()["data"]["id"]

        # Endi TAKEN kodini olishga urinamiz
        resp = client.put(f"/api/v1/students/{student_id}", json={"student_code": "TAKEN"})
        assert resp.status_code == 409

    def test_update_same_student_code_allowed(self, client, admin_cookie, sample_student):
        """O'z student_code'ini yuborishga ruxsat (exclude_id ishlaydi)."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.put(
            f"/api/v1/students/{sample_student.id}",
            json={"student_code": "UZ240001", "full_name": "Yangi Ism"},
        )
        assert resp.status_code == 200

    def test_update_not_found_returns_404(self, client, admin_cookie):
        import uuid
        client.cookies.set("access_token", admin_cookie)
        resp = client.put(f"/api/v1/students/{uuid.uuid4()}", json={"full_name": "X"})
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DELETE /students/{id} — O'CHIRISH
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteStudent:

    def test_delete_requires_auth(self, client, sample_student):
        resp = client.delete(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 401

    def test_delete_requires_editor(self, client, staff_cookie, sample_student):
        client.cookies.set("access_token", staff_cookie)
        resp = client.delete(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 403

    def test_delete_success_returns_204(self, client, admin_cookie, sample_student):
        """Muvaffaqiyatli o'chirish → 204 No Content."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.delete(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 204

    def test_delete_removes_from_db(self, client, admin_cookie, test_db, sample_student):
        """O'chirilgandan keyin DB'da topilmaydi."""
        student_id = sample_student.id
        client.cookies.set("access_token", admin_cookie)
        client.delete(f"/api/v1/students/{student_id}")
        remaining = test_db.query(Student).filter(Student.id == student_id).first()
        assert remaining is None

    def test_delete_twice_second_returns_404(self, client, admin_cookie, sample_student):
        """Ikki marta o'chirish — ikkinchisida 404."""
        client.cookies.set("access_token", admin_cookie)
        client.delete(f"/api/v1/students/{sample_student.id}")
        resp = client.delete(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 404

    def test_delete_not_found_returns_404(self, client, admin_cookie):
        import uuid
        client.cookies.set("access_token", admin_cookie)
        resp = client.delete(f"/api/v1/students/{uuid.uuid4()}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 7. POST /students/{id}/copy — NUSXALASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestCopyStudent:

    def test_copy_requires_auth(self, client, sample_student):
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={"student_code": "COPY001", "email": "copy@t.com"},
        )
        assert resp.status_code == 401

    def test_copy_requires_editor(self, client, staff_cookie, sample_student):
        client.cookies.set("access_token", staff_cookie)
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={"student_code": "COPY001", "email": "copy@t.com"},
        )
        assert resp.status_code == 403

    def test_copy_success(self, client, admin_cookie, sample_student):
        """Nusxalash → 201, yangi talaba yaratiladi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={"student_code": "COPY001", "email": "copy@test.com"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["student_code"] == "COPY001"
        assert data["email"] == "copy@test.com"

    def test_copy_inherits_source_name(self, client, admin_cookie, sample_student):
        """full_name va kana_name manba talabadan olinadi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={"student_code": "COPY002", "email": "copy2@test.com"},
        )
        data = resp.json()["data"]
        assert data["full_name"] == sample_student.full_name
        assert data["kana_name"] == sample_student.kana_name

    def test_copy_overrides_name_if_provided(self, client, admin_cookie, sample_student):
        """full_name berilsa, manbadan emas shu ishlatiladi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={
                "student_code": "COPY003",
                "email": "copy3@test.com",
                "full_name": "Override Ism",
            },
        )
        assert resp.json()["data"]["full_name"] == "Override Ism"

    def test_copy_avatar_url_is_null(self, client, admin_cookie, test_db):
        """Nusxada avatar_url None bo'ladi (S3 URL izolyatsiyasi)."""
        source = Student(
            full_name="Avatarli",
            kana_name="ア",
            student_code="AV001",
            email="av@t.com",
            avatar_url="https://s3.example.com/avatars/original.jpg",
        )
        test_db.add(source)
        test_db.commit()
        test_db.refresh(source)

        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{source.id}/copy",
            json={"student_code": "AV002", "email": "av2@t.com"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["avatar_url"] is None

    def test_copy_duplicate_code_returns_409(self, client, admin_cookie, sample_student):
        """Nusxada allaqachon mavjud student_code → 409."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{sample_student.id}/copy",
            json={"student_code": "UZ240001", "email": "new@t.com"},
        )
        assert resp.status_code == 409

    def test_copy_source_not_found_returns_404(self, client, admin_cookie):
        import uuid
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            f"/api/v1/students/{uuid.uuid4()}/copy",
            json={"student_code": "X001", "email": "x@t.com"},
        )
        assert resp.status_code == 404
