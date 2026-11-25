import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main


def test_public_content_is_explicitly_published_and_admin_managed(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setenv("DESK_SETUP_KEY", "demo-test-key")
    with TestClient(main.app) as client:
        admin_data = {"name": "Admin", "email": "admin@example.com", "password": "strong-secret", "role": "admin"}
        assert client.post("/api/v1/desk/setup", json=admin_data, headers={"X-Setup-Key": "demo-test-key"}).status_code == 201
        login = client.post("/api/v1/desk/login", json={"email": admin_data["email"], "password": admin_data["password"]}).json()
        auth = {"Authorization": "Bearer " + login["token"]}
        assert client.get("/api/v1/desk/public/packages").json() == []
        assert client.get("/api/v1/desk/admin/public/packages").status_code == 401
        package = {"name": "باقة بداية", "description": "باقة تصميم تجريبية للمدرسين", "price_egp": 500, "image_count": 3, "video_count": 1, "revision_count": 2, "delivery_days": 5, "published": False}
        created = client.post("/api/v1/desk/admin/public/packages", headers=auth, json=package)
        assert created.status_code == 201
        assert client.get("/api/v1/desk/public/packages").json() == []
        package["published"] = True
        assert client.patch(f"/api/v1/desk/admin/public/packages/{created.json()['id']}", headers=auth, json=package).status_code == 200
        assert len(client.get("/api/v1/desk/public/packages").json()) == 1

        teacher = {"slug": "mona-hassan", "name": "منى حسن", "subject": "لغة إنجليزية", "bio": "مدرسة لغة إنجليزية تشرح المنهج للطلاب بطريقة عملية.", "published": False}
        teacher_id = client.post("/api/v1/desk/admin/public/teachers", headers=auth, json=teacher).json()["id"]
        work = {"teacher_id": teacher_id, "title": "إعلان مراجعة", "description": "نموذج تصميم لإعلان مراجعة اللغة الإنجليزية.", "kind": "image", "url": "https://drive.google.com/file/d/example", "published": True}
        assert client.post("/api/v1/desk/admin/public/work", headers=auth, json=work).status_code == 201
        assert client.get("/api/v1/desk/public/teachers").json() == []
        assert client.get("/api/v1/desk/public/work").json() == []
        assert client.get("/api/v1/desk/public/teachers/mona-hassan").status_code == 404
        teacher["published"] = True
        assert client.patch(f"/api/v1/desk/admin/public/teachers/{teacher_id}", headers=auth, json=teacher).status_code == 200
        assert len(client.get("/api/v1/desk/public/work").json()) == 1
        assert len(client.get("/api/v1/desk/public/teachers/mona-hassan").json()["works"]) == 1
        assert client.post("/api/v1/desk/admin/public/work", json=work).status_code == 401
    engine.dispose()
