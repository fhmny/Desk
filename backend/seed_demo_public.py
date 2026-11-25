"""Add fake public pages and packages to the isolated desk-demo.db only."""
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.main import Base, PublicPackage, PublicTeacher, PublicWork


DEMO_PATH = Path(__file__).resolve().parent / "desk-demo.db"


def seed_public(path: Path = DEMO_PATH) -> dict[str, int]:
    path = Path(path).resolve()
    if not path.exists() or path.name != "desk-demo.db":
        raise FileNotFoundError("Create desk-demo.db with seed_demo.py first")
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            if db.scalar(select(PublicPackage.id).limit(1)) or db.scalar(select(PublicTeacher.id).limit(1)):
                return {"packages": 0, "teachers": 0, "works": 0}
            teachers = [
                PublicTeacher(slug="ahmed-ibrahim", name="أحمد إبراهيم", subject="رياضيات", bio="مدرس رياضيات بيقدم شرحًا مبسطًا ومراجعات لطلاب المرحلة الثانوية.", facebook="https://www.facebook.com/example", youtube="https://www.youtube.com/@example", published=True),
                PublicTeacher(slug="mona-hassan", name="منى حسن", subject="لغة إنجليزية", bio="مدرسة لغة إنجليزية تركز على الفهم والتدريب العملي والمراجعة المنظمة.", tiktok="https://www.tiktok.com/@example", published=True),
                PublicTeacher(slug="khaled-samir", name="خالد سمير", subject="فيزياء", bio="مدرس فيزياء يشرح المفاهيم العلمية بتجارب وأمثلة قريبة من الطلاب.", youtube="https://www.youtube.com/@example", published=True),
            ]
            db.add_all(teachers)
            db.flush()
            packages = [
                PublicPackage(name="بداية", description="للمدرس اللي عايز حضورًا ثابتًا على السوشيال ميديا.", price_egp=490, image_count=4, video_count=0, revision_count=1, delivery_days=5, published=True),
                PublicPackage(name="نمو", description="تصميمات وفيديوهات قصيرة لإعلانات الكورسات والمراجعات.", price_egp=990, image_count=6, video_count=2, revision_count=2, delivery_days=7, featured=True, published=True),
                PublicPackage(name="ستوديو", description="مساحة إنتاج أوسع لموسم كامل من المحتوى التعليمي.", price_egp=1890, image_count=10, video_count=4, revision_count=3, delivery_days=10, published=True),
            ]
            works = [
                PublicWork(teacher_id=teachers[0].id, title="حملة مراجعة الجبر", description="نموذج منشور للإعلان عن مراجعة الجبر للمرحلة الثانوية.", kind="image", url="https://example.com/demo/algebra-poster", published=True),
                PublicWork(teacher_id=teachers[1].id, title="تيزر كورس المحادثة", description="نموذج فيديو قصير يعرّف الطلاب ببرنامج المحادثة.", kind="video", url="https://example.com/demo/english-reel", published=True),
                PublicWork(teacher_id=teachers[2].id, title="شرح تجربة فيزياء", description="نموذج مونتاج لمقطع تعليمي قصير من حصة عملية.", kind="video", url="https://example.com/demo/physics-video", published=True),
            ]
            db.add_all(packages + works)
            db.commit()
            return {"packages": len(packages), "teachers": len(teachers), "works": len(works)}
    finally:
        engine.dispose()


if __name__ == "__main__":
    counts = seed_public()
    print(f"Demo public content: {counts}")
