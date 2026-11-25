import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from seed_demo import DEMO_PASSWORD, create_demo_database


def test_demo_seed_is_isolated_complete_and_non_destructive(tmp_path, monkeypatch):
    path = tmp_path / "desk-demo.db"
    assert create_demo_database(path) == {"users": 6, "requests": 7}
    with pytest.raises(FileExistsError):
        create_demo_database(path)

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(engine, expire_on_commit=False))
    with TestClient(main.app) as client:
        def headers(email):
            response = client.post("/api/v1/desk/login", json={"email": email, "password": DEMO_PASSWORD})
            assert response.status_code == 200
            return {"Authorization": "Bearer " + response.json()["token"]}

        admin = headers("admin@desk.demo")
        sara = headers("sara@desk.demo")
        omar = headers("omar@desk.demo")
        ahmed = headers("ahmed@desk.demo")
        assert len(client.get("/api/v1/desk/requests", headers=admin).json()) == 7
        assert len(client.get("/api/v1/desk/requests", headers=sara).json()) == 5
        assert len(client.get("/api/v1/desk/requests", headers=omar).json()) == 2
        assert len(client.get("/api/v1/desk/requests", headers=ahmed).json()) == 3
        quota = client.get("/api/v1/desk/me", headers=ahmed).json()["quotas"]
        assert quota["image"] == {"total": 5, "reserved": 0, "completed": 1, "available": 4}
        assert quota["video"] == {"total": 2, "reserved": 1, "completed": 0, "available": 1}
        assert client.get("/api/v1/desk/requests/1", headers=omar).status_code == 404
    engine.dispose()
