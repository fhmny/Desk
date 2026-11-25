"""Create an isolated, fully fake Creative Desk database for local testing.

Run from desk/backend: py -3 seed_demo.py
Then start the API with DESK_DATABASE_URL=sqlite:///./desk-demo.db.
Existing files are never overwritten.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import Audit, Base, Link, Message, Request, User, hash_password, now


DEMO_PATH = Path(__file__).resolve().parent / "desk-demo.db"
DEMO_PASSWORD = "Demo12345!"


def create_demo_database(path: Path = DEMO_PATH) -> dict[str, int]:
    """Create a new database; refuse to touch a file that already exists."""
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError(f"Demo database already exists: {path}")
    engine = create_engine(f"sqlite:///{path}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            password_hash = hash_password(DEMO_PASSWORD)
            people = {
                "admin": User(name="مدير المكتب التجريبي", email="admin@desk.demo", password_hash=password_hash, role="admin"),
                "designer_sara": User(name="سارة محمد", email="sara@desk.demo", password_hash=password_hash, role="designer"),
                "designer_omar": User(name="عمر خالد", email="omar@desk.demo", password_hash=password_hash, role="designer"),
                "teacher_ahmed": User(name="أحمد إبراهيم", email="ahmed@desk.demo", password_hash=password_hash, role="teacher", subject="رياضيات", image_limit=5, video_limit=2, facebook="https://www.facebook.com/example", tiktok="https://www.tiktok.com/@example", youtube="https://www.youtube.com/@example"),
                "teacher_mona": User(name="منى حسن", email="mona@desk.demo", password_hash=password_hash, role="teacher", subject="لغة إنجليزية", image_limit=3, video_limit=1, facebook="https://www.facebook.com/example"),
                "teacher_khaled": User(name="خالد سمير", email="khaled@desk.demo", password_hash=password_hash, role="teacher", subject="فيزياء", image_limit=4, video_limit=2, youtube="https://www.youtube.com/@example"),
            }
            db.add_all(people.values())
            db.flush()
            people["teacher_ahmed"].designer_id = people["designer_sara"].id
            people["teacher_mona"].designer_id = people["designer_sara"].id
            people["teacher_khaled"].designer_id = people["designer_omar"].id

            specs = [
                ("teacher_ahmed", "image", "بوست مراجعة الجبر", "صمم بوست للمراجعة النهائية. استخدم درجات الأزرق، واكتب موعد المراجعة يوم الخميس الساعة السادسة.", "completed", 8),
                ("teacher_ahmed", "video", "ريل إعلان الحصة الجديدة", "مونتاج ريل عمودي 30 ثانية من مقاطع الحصة، مع عنوان واضح في أول ثلاث ثوانٍ.", "in_progress", 5),
                ("teacher_ahmed", "image", "غلاف امتحان تجريبي", "محتاج غلاف بسيط للامتحان التجريبي للصف الثالث، مع مكان لكتابة الدرجة والاسم.", "submitted", 1),
                ("teacher_mona", "image", "قالب كلمات الأسبوع", "صممي قالب ثابت لكلمات الأسبوع بالإنجليزي، مناسب للنشر على فيسبوك وإنستجرام.", "revision_requested", 6),
                ("teacher_mona", "video", "تيزر كورس المحادثة", "فيديو قصير يعرّف بكورس المحادثة ومواعيد الاشتراك. المقاس 9:16.", "submitted", 2),
                ("teacher_khaled", "video", "مونتاج تجربة المعمل", "رتب لقطات تجربة المعمل في فيديو تعليمي مدته أقل من دقيقة مع عناوين الخطوات.", "completed", 10),
                ("teacher_khaled", "image", "بوست قانون نيوتن", "صمم صورة مبسطة تعرض قوانين نيوتن الثلاثة في شكل مناسب للطلاب.", "accepted", 3),
            ]
            for index, (teacher_key, kind, title, brief, state, days_ago) in enumerate(specs, start=1):
                teacher = people[teacher_key]
                designer = db.get(User, teacher.designer_id)
                created = now() - timedelta(days=days_ago)
                item = Request(teacher_id=teacher.id, designer_id=designer.id, kind=kind, title=title, brief=brief, status=state, created_at=created, updated_at=created + timedelta(days=1))
                db.add(item)
                db.flush()
                db.add(Link(request_id=item.id, author_id=teacher.id, kind="reference", label="مرجع تجريبي من المدرس", url=f"https://www.youtube.com/watch?v=demo{index}", created_at=created))
                db.add(Message(request_id=item.id, author_id=teacher.id, body="ده وصف الطلب. لو محتاج أي تفاصيل زيادة اسألني هنا.", created_at=created + timedelta(minutes=5)))
                db.add(Message(request_id=item.id, author_id=designer.id, body="وصلني الطلب، هراجع المراجع وأبدأ الشغل.", created_at=created + timedelta(minutes=25)))
                if state != "submitted":
                    db.add(Audit(actor_id=designer.id, request_id=item.id, action="accept", created_at=created + timedelta(minutes=30)))
                if state in {"in_progress", "completed", "revision_requested"}:
                    db.add(Link(request_id=item.id, author_id=designer.id, kind="draft", label="مسودة تجريبية — الرابط غير حقيقي", url=f"https://drive.google.com/drive/folders/DEMO_DRAFT_{index}", created_at=created + timedelta(hours=4)))
                    db.add(Message(request_id=item.id, author_id=designer.id, body="حضرت مسودة أولى. الرابط تجريبي لعرض شكل النظام فقط.", created_at=created + timedelta(hours=4)))
                if state in {"completed", "revision_requested"}:
                    db.add(Link(request_id=item.id, author_id=designer.id, kind="final", label="تسليم تجريبي — الرابط غير حقيقي", url=f"https://drive.google.com/drive/folders/DEMO_FINAL_{index}", created_at=created + timedelta(hours=8)))
                    db.add(Message(request_id=item.id, author_id=designer.id, body="تم التسليم. ده رابط Drive تجريبي، استبدله بالرابط الحقيقي عند الشغل الفعلي.", created_at=created + timedelta(hours=8)))
                    db.add(Audit(actor_id=designer.id, request_id=item.id, action="deliver", created_at=created + timedelta(hours=8)))
                if state == "revision_requested":
                    db.add(Message(request_id=item.id, author_id=teacher.id, body="ممكن نكبر عنوان الكلمات ونغير لون الخلفية؟", created_at=created + timedelta(days=1)))
                    db.add(Audit(actor_id=teacher.id, request_id=item.id, action="revise", created_at=created + timedelta(days=1)))
                db.add(Audit(actor_id=teacher.id, request_id=item.id, action="created", created_at=created))
            db.commit()
            return {"users": len(people), "requests": len(specs)}
    except Exception:
        engine.dispose()
        path.unlink(missing_ok=True)
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        counts = create_demo_database()
    except FileExistsError as exc:
        raise SystemExit(f"{exc}\nNo data was changed. Use the existing demo or move it aside manually.") from exc
    print(f"Created {DEMO_PATH} with {counts['users']} fake users and {counts['requests']} fake requests.")
    print("Demo password for every account: Demo12345!")
