"""
Issue 02: Cookie asosidagi JWT Autentifikatsiya tizimi

Testlar quyidagilarni tekshiradi:
1. security.py — parol hash va JWT funksiyalari (unit testlar)
2. POST /auth/login — muvaffaqiyatli va muvaffaqiyatsiz scenariolar
3. POST /auth/logout — cookie o'chirilishi
4. GET /auth/me — joriy foydalanuvchi ma'lumoti
5. get_current_user dependency — barcha xatolik holatlari
6. require_admin dependency — 403 Forbidden holati
"""

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from jose import jwt

from src.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)
from src.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SECURITY UTILS UNIT TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    """bcrypt parol hashlash va tekshirish."""

    def test_get_password_hash_returns_string(self):
        hashed = get_password_hash("mypassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hashed_password_is_not_plain(self):
        plain = "mypassword"
        hashed = get_password_hash(plain)
        assert hashed != plain

    def test_verify_password_correct(self):
        plain = "secret123"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_wrong(self):
        hashed = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_different_hashes(self):
        """bcrypt salt tufayli bir xil parol har safar boshqa hash beradi."""
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2
        # Lekin ikkalasi ham tekshirishdan o'tadi
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True

    def test_empty_password_hash(self):
        """Bo'sh parol ham hashlana oladi (tekshiruv domenga bog'liq)."""
        hashed = get_password_hash("")
        assert isinstance(hashed, str)


class TestJWT:
    """JWT yaratish va dekodlash."""

    def test_create_access_token_returns_string(self):
        token = create_access_token(subject="user-id-123", role="admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_admin_role(self):
        token = create_access_token(subject="uid", role="admin")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["role"] == "admin"

    def test_create_token_with_staff_role(self):
        token = create_access_token(subject="uid", role="staff")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["role"] == "staff"

    def test_token_payload_has_sub(self):
        token = create_access_token(subject="my-user-id", role="staff")
        payload = decode_access_token(token)
        assert payload["sub"] == "my-user-id"

    def test_token_payload_has_exp(self):
        token = create_access_token(subject="uid", role="staff")
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_decode_invalid_token_returns_none(self):
        result = decode_access_token("bu.yaroqsiz.token")
        assert result is None

    def test_decode_empty_token_returns_none(self):
        result = decode_access_token("")
        assert result is None

    def test_decode_token_wrong_secret_returns_none(self):
        """Boshqa secret bilan imzolangan token qabul qilinmaydi."""
        fake_token = jwt.encode(
            {"sub": "uid", "role": "staff"},
            "wrong-secret",
            algorithm=settings.JWT_ALGORITHM,
        )
        result = decode_access_token(fake_token)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# 2. POST /auth/login TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    """Login endpointi."""

    def test_login_success_admin(self, client, admin_user):
        """Admin muvaffaqiyatli login qiladi."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "secret123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "user" in body["data"]
        assert body["data"]["user"]["email"] == "admin@test.com"
        assert body["data"]["user"]["role"] == "admin"

    def test_login_success_staff(self, client, staff_user):
        """Staff muvaffaqiyatli login qiladi."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "staff@test.com", "password": "secret123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["user"]["role"] == "staff"

    def test_login_sets_httponly_cookie(self, client, admin_user):
        """Cookie access_token nomi bilan o'rnatiladi."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "secret123"},
        )
        assert "access_token" in resp.cookies

    def test_login_token_not_in_body(self, client, admin_user):
        """Token body'da qaytarilmaydi (xavfsizlik)."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "secret123"},
        )
        body = resp.json()
        # Token body'da bo'lmasligi kerak
        assert "token" not in body
        assert "access_token" not in str(body.get("data", {}))

    def test_login_wrong_password_returns_401(self, client, admin_user):
        """Noto'g'ri parol → 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_wrong_email_returns_401(self, client, admin_user):
        """Mavjud bo'lmagan email → 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "notexist@test.com", "password": "secret123"},
        )
        assert resp.status_code == 401

    def test_login_invalid_email_format_returns_422(self, client):
        """Email format noto'g'ri → 422 Validation Error."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "notanemail", "password": "pass"},
        )
        assert resp.status_code == 422

    def test_login_missing_fields_returns_422(self, client):
        """Majburiy maydonlar yo'q → 422."""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 3. POST /auth/logout TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogout:
    """Logout endpointi."""

    def test_logout_success(self, client, admin_cookie):
        """Login qilingan foydalanuvchi muvaffaqiyatli chiqadi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_logout_without_cookie_returns_401(self, client):
        """Cookie yo'q holda logout → 401."""
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401

    def test_logout_clears_cookie(self, client, admin_cookie):
        """Logout qilgandan keyin cookie o'chadi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        # Cookie o'chirilgan bo'lishi kerak (Set-Cookie: access_token=; ...)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GET /auth/me TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetMe:
    """Joriy foydalanuvchi ma'lumoti."""

    def test_get_me_admin(self, client, admin_cookie):
        """Admin o'z ma'lumotini oladi."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["user"]["email"] == "admin@test.com"
        assert body["data"]["user"]["role"] == "admin"

    def test_get_me_staff(self, client, staff_cookie):
        """Staff o'z ma'lumotini oladi."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["data"]["user"]["role"] == "staff"

    def test_get_me_without_cookie_returns_401(self, client):
        """Cookie yo'q → 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_me_with_invalid_token_returns_401(self, client):
        """Yaroqsiz token → 401."""
        client.cookies.set("access_token", "invalid.token.here")
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_me_response_has_no_password(self, client, admin_cookie):
        """Javobda password_hash bo'lmasligi kerak (xavfsizlik)."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/auth/me")
        user_data = resp.json()["data"]["user"]
        assert "password_hash" not in user_data
        assert "password" not in user_data

    def test_get_me_response_has_required_fields(self, client, admin_cookie):
        """Javobda id, email, full_name, role bo'lishi kerak."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/auth/me")
        user_data = resp.json()["data"]["user"]
        assert "id" in user_data
        assert "email" in user_data
        assert "full_name" in user_data
        assert "role" in user_data


# ═══════════════════════════════════════════════════════════════════════════════
# 5. require_admin DEPENDENCY TESTLARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequireAdmin:
    """require_admin dependency — 403 Forbidden holati."""

    def test_staff_cannot_create_student(self, client, staff_cookie, sample_student):
        """Tahrirlash huquqisiz foydalanuvchi student yarata olmaydi → 403."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Yangi Talaba",
                "kana_name": "ヤンギ",
                "student_code": "YT001",
                "email": "yangi@test.com",
            },
        )
        assert resp.status_code == 403

    def test_admin_can_create_student(self, client, admin_cookie):
        """Admin student yarata oladi → 201."""
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Yangi Talaba",
                "kana_name": "ヤンギ",
                "student_code": "YT001",
                "email": "yangi@test.com",
            },
        )
        assert resp.status_code == 201

    def test_staff_cannot_delete_student(self, client, staff_cookie, sample_student):
        """Tahrirlash huquqisiz foydalanuvchi student o'chira olmaydi → 403."""
        client.cookies.set("access_token", staff_cookie)
        resp = client.delete(f"/api/v1/students/{sample_student.id}")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create(self, client):
        """Login qilinmagan foydalanuvchi → 401 (403 emas)."""
        resp = client.post(
            "/api/v1/students/",
            json={"full_name": "A", "kana_name": "A", "student_code": "A001", "email": "a@t.com"},
        )
        assert resp.status_code == 401
