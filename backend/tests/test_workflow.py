import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setenv("DESK_SETUP_KEY", "test-setup-key")
    with TestClient(main.app) as client:
        yield client
    engine.dispose()


def create_admin(client):
    data = {"name": "Admin", "email": "admin@example.com", "password": "strong-secret", "role": "admin"}
    assert client.post("/api/v1/desk/setup", json=data).status_code == 403
    assert client.post("/api/v1/desk/setup", json=data, headers={"X-Setup-Key": "test-setup-key"}).status_code == 201
    assert client.post("/api/v1/desk/setup", json=data, headers={"X-Setup-Key": "test-setup-key"}).status_code == 403
    return login(client, data["email"], data["password"])


def login(client, email, password):
    result = client.post("/api/v1/desk/login", json={"email": email, "password": password})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["token"]}


def add_user(client, admin, name, email, role):
    response = client.post("/api/v1/desk/users", headers=admin, json={"name": name, "email": email, "password": "strong-secret", "role": role})
    assert response.status_code == 201, response.text
    return response.json()["id"], login(client, email, "strong-secret")


def test_full_request_quota_chat_delivery_and_isolation(client):
    admin = create_admin(client)
    designer_id, designer = add_user(client, admin, "Designer A", "a@example.com", "designer")
    _, other_designer = add_user(client, admin, "Designer B", "b@example.com", "designer")
    teacher_id, teacher = add_user(client, admin, "Teacher", "teacher@example.com", "teacher")
    assignment = client.patch(f"/api/v1/desk/teachers/{teacher_id}/assignment", headers=admin, json={"designer_id": designer_id, "image_limit": 1, "video_limit": 2})
    assert assignment.status_code == 200

    request = client.post("/api/v1/desk/requests", headers=teacher, json={"kind": "image", "title": "Exam poster", "brief": "Create a poster for the exam", "references": ["https://youtube.com/watch?v=1"]})
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    assert client.get(f"/api/v1/desk/requests/{request_id}", headers=other_designer).status_code == 404
    assert client.get("/api/v1/desk/requests", headers=other_designer).json() == []
    assert client.get("/api/v1/desk/admin/audit", headers=designer).status_code == 403
    assert client.post(f"/api/v1/desk/requests/{request_id}/messages", headers=teacher, json={"body": "Use blue"}).status_code == 201
    assert client.post(f"/api/v1/desk/requests/{request_id}/messages", headers=designer, json={"body": "Which shade?"}).status_code == 201
    detail = client.get(f"/api/v1/desk/requests/{request_id}", headers=admin).json()
    assert len(detail["messages"]) == 2
    assert detail["links"][0]["kind"] == "reference"

    assert client.post(f"/api/v1/desk/requests/{request_id}/accept", headers=designer).status_code == 200
    counts = client.get("/api/v1/desk/me", headers=teacher).json()["quotas"]
    assert counts["image"] == {"total": 1, "reserved": 1, "completed": 0, "available": 0}
    assert counts["video"]["available"] == 2
    assert client.post(f"/api/v1/desk/requests/{request_id}/deliver", headers=designer).status_code == 409
    assert client.post(f"/api/v1/desk/requests/{request_id}/links", headers=designer, json={"url": "https://evil.example/file", "label": "Bad", "kind": "final"}).status_code == 422
    assert client.post(f"/api/v1/desk/requests/{request_id}/links", headers=designer, json={"url": "https://drive.google.com/file/d/abc", "label": "Final", "kind": "final"}).status_code == 201
    assert client.post(f"/api/v1/desk/requests/{request_id}/deliver", headers=designer).status_code == 200
    assert client.get("/api/v1/desk/me", headers=teacher).json()["quotas"]["image"]["completed"] == 1
    assert client.post(f"/api/v1/desk/requests/{request_id}/deliver", headers=teacher).status_code == 409
    assert client.post(f"/api/v1/desk/requests/{request_id}/revise", headers=teacher).status_code == 200
    assert client.get("/api/v1/desk/me", headers=teacher).json()["quotas"]["image"]["completed"] == 1
    assert client.post(f"/api/v1/desk/requests/{request_id}/deliver", headers=designer).status_code == 200
    assert client.post(f"/api/v1/desk/requests/{request_id}/deliver", headers=designer).status_code == 409
    assert client.get("/api/v1/desk/me", headers=teacher).json()["quotas"]["image"] == {"total": 1, "reserved": 0, "completed": 1, "available": 0}
    assert client.get("/api/v1/desk/users", headers=admin).json()[-1]["quotas"]["image"]["completed"] == 1
    assert any(event["action"] == "deliver" for event in client.get("/api/v1/desk/admin/audit", headers=admin).json())
    assert client.patch(f"/api/v1/desk/teachers/{teacher_id}/assignment", headers=admin, json={"designer_id": designer_id, "image_limit": 0, "video_limit": 2}).status_code == 409


def test_admin_only_accounts_and_cancel_releases_slot(client):
    admin = create_admin(client)
    designer_id, designer = add_user(client, admin, "Designer", "designer@example.com", "designer")
    teacher_id, teacher = add_user(client, admin, "Teacher", "teacher@example.com", "teacher")
    assert client.post("/api/v1/desk/users", headers=teacher, json={"name": "Hacker", "email": "h@example.com", "password": "abcdefgh", "role": "designer"}).status_code == 403
    client.patch(f"/api/v1/desk/teachers/{teacher_id}/assignment", headers=admin, json={"designer_id": designer_id, "image_limit": 1, "video_limit": 0})
    request = client.post("/api/v1/desk/requests", headers=teacher, json={"kind": "image", "title": "Social post", "brief": "Make a blue social post"}).json()
    request_id = request["id"]
    assert client.post(f"/api/v1/desk/requests/{request_id}/accept", headers=designer).status_code == 200
    assert client.post(f"/api/v1/desk/admin/requests/{request_id}/cancel", headers=admin, json={"reason": "Teacher changed plan"}).status_code == 200
    assert client.get("/api/v1/desk/me", headers=teacher).json()["quotas"]["image"]["available"] == 1


def test_reassignment_moves_all_teacher_requests_and_revokes_old_designer(client):
    admin = create_admin(client)
    first_id, first = add_user(client, admin, "Designer A", "a@example.com", "designer")
    second_id, second = add_user(client, admin, "Designer B", "b@example.com", "designer")
    teacher_id, teacher = add_user(client, admin, "Teacher", "teacher@example.com", "teacher")
    assignment_url = f"/api/v1/desk/teachers/{teacher_id}/assignment"
    assert client.patch(assignment_url, headers=admin, json={"designer_id": first_id, "image_limit": 2, "video_limit": 1}).status_code == 200
    created = client.post("/api/v1/desk/requests", headers=teacher, json={"kind": "image", "title": "New poster", "brief": "Create a poster for this lesson"}).json()
    request_url = f"/api/v1/desk/requests/{created['id']}"
    assert client.get(request_url, headers=first).status_code == 200
    assert client.patch(assignment_url, headers=admin, json={"designer_id": second_id, "image_limit": 2, "video_limit": 1}).status_code == 200
    assert client.get(request_url, headers=first).status_code == 404
    assert client.get("/api/v1/desk/requests", headers=first).json() == []
    assert client.post(request_url + "/messages", headers=first, json={"body": "I should not see this"}).status_code == 404
    assert client.get(request_url, headers=second).status_code == 200
    assert client.post(request_url + "/messages", headers=second, json={"body": "I am your designer now"}).status_code == 201
    next_request = client.post("/api/v1/desk/requests", headers=teacher, json={"kind": "video", "title": "Lesson video", "brief": "Edit this video for class"}).json()
    assert next_request["designer_id"] == second_id
    assert len(client.get("/api/v1/desk/requests", headers=second).json()) == 2
