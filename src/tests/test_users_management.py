from uuid import uuid4

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.models.user import User, UserRole

class TestUsersManagement:
    
    def test_get_users_admin_can_access(self, client: TestClient, admin_cookie: str):
        client.cookies.set("access_token", admin_cookie)
        resp = client.get("/api/v1/users/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) > 0

    def test_get_users_staff_cannot_access(self, client: TestClient, staff_cookie: str):
        client.cookies.set("access_token", staff_cookie)
        resp = client.get("/api/v1/users/")
        assert resp.status_code == 403

    def test_create_user_admin_can_create(self, client: TestClient, admin_cookie: str):
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "new_staff@test.com",
                "password": "password123",
                "full_name": "New Staff",
                "role": "staff"
            }
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["email"] == "new_staff@test.com"
        assert body["data"]["role"] == "staff"

    def test_create_user_duplicate_email(self, client: TestClient, admin_cookie: str, admin_user: User):
        client.cookies.set("access_token", admin_cookie)
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": admin_user.email,
                "password": "password123",
                "full_name": "Duplicate User",
                "role": "staff"
            }
        )
        assert resp.status_code == 409

    def test_update_user_role(self, client: TestClient, admin_cookie: str, staff_user: User):
        client.cookies.set("access_token", admin_cookie)
        resp = client.put(
            f"/api/v1/users/{staff_user.id}/role",
            json={"role": "admin"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["role"] == "admin"

    def test_delete_user(self, client: TestClient, admin_cookie: str, staff_user: User):
        client.cookies.set("access_token", admin_cookie)
        resp = client.delete(f"/api/v1/users/{staff_user.id}")
        assert resp.status_code == 204

    def test_admin_cannot_delete_himself(self, client: TestClient, admin_cookie: str, admin_user: User):
        client.cookies.set("access_token", admin_cookie)
        resp = client.delete(f"/api/v1/users/{admin_user.id}")
        assert resp.status_code == 400
