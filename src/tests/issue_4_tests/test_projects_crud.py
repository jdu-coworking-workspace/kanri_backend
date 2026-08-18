import uuid
from datetime import date
from typing import Dict

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.models.project import Project, ProjectStatus, ProjectCategory
from src.models.student import Student


def get_base_payload() -> Dict:
    return {
        "name": "New API Project",
        "overview": "Bu yangi loyiha",
        "start_date": "2026-03-01",
        "status": "planned",
        "category": "it",
    }


class TestProjectCRUD:

    def test_create_project_requires_editor(
        self, client: TestClient, staff_cookie: str
    ):
        client.cookies.set("access_token", staff_cookie)
        response = client.post("/api/v1/projects/", json=get_base_payload())
        assert response.status_code == 403

    def test_create_project_success(
        self, client: TestClient, admin_cookie: str, test_db: Session
    ):
        client.cookies.set("access_token", admin_cookie)
        payload = get_base_payload()
        response = client.post("/api/v1/projects/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New API Project"
        assert data["data"]["category"] == "it"
        
        # Verify in DB
        db_project = test_db.query(Project).filter_by(name="New API Project").first()
        assert db_project is not None
        assert db_project.status == ProjectStatus.PLANNED

    def test_create_project_duplicate_name_fails(
        self, client: TestClient, admin_cookie: str, sample_project: Project
    ):
        client.cookies.set("access_token", admin_cookie)
        payload = get_base_payload()
        payload["name"] = sample_project.name
        
        response = client.post("/api/v1/projects/", json=payload)
        assert response.status_code == 409

    def test_get_projects_list(
        self, client: TestClient, staff_cookie: str, sample_project: Project
    ):
        client.cookies.set("access_token", staff_cookie)
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert "meta" in data
        assert data["meta"]["total"] >= 1

    def test_get_project_detail(
        self, client: TestClient, staff_cookie: str, sample_project: Project
    ):
        client.cookies.set("access_token", staff_cookie)
        response = client.get(f"/api/v1/projects/{sample_project.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(sample_project.id)
        assert data["data"]["name"] == sample_project.name

    def test_update_project(
        self, client: TestClient, admin_cookie: str, sample_project: Project, test_db: Session
    ):
        client.cookies.set("access_token", admin_cookie)
        payload = {"status": "done", "overview": "Updated overview"}
        
        response = client.put(f"/api/v1/projects/{sample_project.id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "done"
        assert data["data"]["overview"] == "Updated overview"
        
        # Verify in DB
        test_db.refresh(sample_project)
        assert sample_project.status == ProjectStatus.DONE

    def test_delete_project(
        self, client: TestClient, admin_cookie: str, sample_project: Project, test_db: Session
    ):
        client.cookies.set("access_token", admin_cookie)
        response = client.delete(f"/api/v1/projects/{sample_project.id}")
        
        assert response.status_code == 204
        
        # Verify in DB
        db_project = test_db.query(Project).filter_by(id=sample_project.id).first()
        assert db_project is None
