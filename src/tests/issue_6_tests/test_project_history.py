# pyrefly: ignore [missing-import]
import pytest
from uuid import uuid4

def test_project_history_created(client, admin_cookie, test_db):
    """Loyiha yaratilganda tarixga 'created' qo'shiladi"""
    client.cookies.set("access_token", admin_cookie)
    
    # 1. Loyiha yaratish
    project_data = {
        "name": "Test History Project",
        "start_date": "2026-01-01",
        "status": "planned",
        "category": "it"
    }
    resp = client.post("/api/v1/projects/", json=project_data)
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]
    
    # 2. Tarixini olish
    resp_history = client.get(f"/api/v1/projects/{project_id}/history")
    assert resp_history.status_code == 200
    
    data = resp_history.json()["data"]
    assert len(data) == 1
    assert data[0]["change_type"] == "created"
    assert data[0]["description"] == "Loyiha yaratildi"

def test_project_history_updated(client, admin_cookie, test_db):
    """Loyiha tahrirlanganda tarixga 'updated' qo'shiladi"""
    client.cookies.set("access_token", admin_cookie)
    
    # 1. Loyiha yaratish
    project_data = {
        "name": "Project Update Test",
        "start_date": "2026-02-01",
        "status": "planned",
        "category": "video"
    }
    resp = client.post("/api/v1/projects/", json=project_data)
    project_id = resp.json()["data"]["id"]
    
    # 2. Loyihani tahrirlash (status va kategoriya)
    update_data = {
        "status": "active",
        "category": "it"
    }
    resp_update = client.put(f"/api/v1/projects/{project_id}", json=update_data)
    assert resp_update.status_code == 200
    
    # 3. Tarixni tekshirish
    resp_history = client.get(f"/api/v1/projects/{project_id}/history")
    data = resp_history.json()["data"]
    
    # Endi 2 ta yozuv bo'lishi kerak: created va updated
    # Eng yangisi 1-o'rinda (descending order)
    assert len(data) == 2
    assert data[0]["change_type"] == "updated"
    assert "holati" in data[0]["description"]
    assert "kategoriyasi" in data[0]["description"]
    assert data[1]["change_type"] == "created"

def test_project_history_unauthorized(client):
    """Tarixni olish uchun avtorizatsiya kerak"""
    resp = client.get(f"/api/v1/projects/{uuid4()}/history")
    assert resp.status_code == 401

def test_project_history_staff_allowed(client, admin_cookie, staff_cookie, test_db):
    """Staff ham loyiha tarixini ko'ra oladi"""
    # 1. Admin yaratadi
    client.cookies.set("access_token", admin_cookie)
    project_data = {
        "name": "Staff History Test",
        "start_date": "2026-01-01",
        "status": "planned",
        "category": "it"
    }
    resp = client.post("/api/v1/projects/", json=project_data)
    project_id = resp.json()["data"]["id"]
    
    # 2. Staff ko'radi
    client.cookies.set("access_token", staff_cookie)
    resp_history = client.get(f"/api/v1/projects/{project_id}/history")
    assert resp_history.status_code == 200
    assert len(resp_history.json()["data"]) == 1
