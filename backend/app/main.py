"""Creative Desk API. Stores text and external URLs only."""
from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request as HttpRequest, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, func, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.getenv("DESK_DATABASE_URL", "sqlite:///./desk.db")
IS_PRODUCTION = os.getenv("DESK_ENV", "development") == "production"
if IS_PRODUCTION and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Production requires a separate PostgreSQL DESK_DATABASE_URL")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    subject: Mapped[str | None] = mapped_column(String(150), nullable=True)
    facebook: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tiktok: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    youtube: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    designer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    image_limit: Mapped[int] = mapped_column(Integer, default=0)
    video_limit: Mapped[int] = mapped_column(Integer, default=0)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Request(Base):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    designer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    brief: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Link(Base):
    __tablename__ = "links"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    url: Mapped[str] = mapped_column(String(2000))
    label: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublicTeacher(Base):
    __tablename__ = "public_teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    subject: Mapped[str] = mapped_column(String(150))
    bio: Mapped[str] = mapped_column(Text)
    facebook: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tiktok: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    youtube: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class PublicWork(Base):
    __tablename__ = "public_works"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("public_teachers.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(2000))
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublicPackage(Base):
    __tablename__ = "public_packages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    price_egp: Mapped[float] = mapped_column(Numeric(10, 2))
    image_count: Mapped[int] = mapped_column(Integer)
    video_count: Mapped[int] = mapped_column(Integer)
    revision_count: Mapped[int] = mapped_column(Integer)
    delivery_days: Mapped[int] = mapped_column(Integer)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


def db_session():
    with SessionLocal() as db:
        yield db


Db = Annotated[Session, Depends(db_session)]


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 300_000)
    return f"{salt}:{digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
        return secrets.compare_digest(hash_password(password, salt).split(":", 1)[1], digest)
    except ValueError:
        return False


def valid_https(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("استخدم رابط HTTPS صحيحًا")
    return url.strip()


def valid_drive(url: str) -> str:
    url = valid_https(url)
    host = urlparse(url).hostname or ""
    if host not in {"drive.google.com", "docs.google.com"}:
        raise ValueError("رابط التسليم يجب أن يكون من Google Drive")
    return url


class Role(str, Enum):
    admin = "admin"
    teacher = "teacher"
    designer = "designer"


class LoginIn(BaseModel):
    email: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=200)


class AdminResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=12, max_length=200)


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=255)
    password: str = Field(min_length=8, max_length=200)
    role: Role
    subject: str | None = None
    facebook: str | None = None
    tiktok: str | None = None
    youtube: str | None = None
    @field_validator("facebook", "tiktok", "youtube")
    @classmethod
    def check_url(cls, value: str | None) -> str | None:
        return valid_https(value) if value else None


class AssignmentIn(BaseModel):
    designer_id: int
    image_limit: int = Field(ge=0)
    video_limit: int = Field(ge=0)


class RequestIn(BaseModel):
    kind: str = Field(pattern="^(image|video)$")
    title: str = Field(min_length=3, max_length=200)
    brief: str = Field(min_length=10, max_length=10000)
    references: list[str] = Field(default_factory=list, max_length=15)
    @field_validator("references")
    @classmethod
    def check_references(cls, urls: list[str]) -> list[str]:
        return [valid_https(url) for url in urls]


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class LinkIn(BaseModel):
    url: str
    label: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern="^(draft|final)$")
    @field_validator("url")
    @classmethod
    def check_drive(cls, url: str) -> str:
        return valid_drive(url)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class PublicTeacherIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=150)
    subject: str = Field(min_length=2, max_length=150)
    bio: str = Field(min_length=10, max_length=3000)
    facebook: str | None = None
    tiktok: str | None = None
    youtube: str | None = None
    published: bool = False
    @field_validator("facebook", "tiktok", "youtube")
    @classmethod
    def social_url(cls, value: str | None) -> str | None:
        return valid_https(value) if value else None


class PublicWorkIn(BaseModel):
    teacher_id: int | None = None
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=3000)
    kind: str = Field(pattern="^(image|video|link)$")
    url: str
    published: bool = False
    @field_validator("url")
    @classmethod
    def work_url(cls, value: str) -> str:
        return valid_https(value)


class PublicPackageIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=10, max_length=3000)
    price_egp: float = Field(ge=0, le=9999999)
    image_count: int = Field(ge=0, le=10000)
    video_count: int = Field(ge=0, le=10000)
    revision_count: int = Field(ge=0, le=1000)
    delivery_days: int = Field(ge=1, le=365)
    featured: bool = False
    published: bool = False


def current_user(db: Db, authorization: Annotated[str | None, Header()] = None) -> User:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not token or not authorization.startswith("Bearer "):
        raise HTTPException(401, "سجّل الدخول أولًا")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_hash))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < now():
        raise HTTPException(401, "انتهت الجلسة")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "الحساب غير متاح")
    return user


Actor = Annotated[User, Depends(current_user)]


def require_role(actor: User, *roles: str):
    if actor.role not in roles:
        raise HTTPException(403, "ليس لديك صلاحية")


def user_out(user: User) -> dict:
    return {key: getattr(user, key) for key in ("id", "name", "email", "role", "active", "subject", "facebook", "tiktok", "youtube", "designer_id", "image_limit", "video_limit")}


def request_out(item: Request) -> dict:
    return {key: getattr(item, key) for key in ("id", "teacher_id", "designer_id", "kind", "title", "brief", "status", "created_at", "updated_at")}


def public_teacher_out(item: PublicTeacher) -> dict:
    return {key: getattr(item, key) for key in ("id", "slug", "name", "subject", "bio", "facebook", "tiktok", "youtube", "published")}


def public_work_out(item: PublicWork) -> dict:
    return {key: getattr(item, key) for key in ("id", "teacher_id", "title", "description", "kind", "url", "published", "created_at")}


def public_package_out(item: PublicPackage) -> dict:
    return {key: getattr(item, key) for key in ("id", "name", "description", "price_egp", "image_count", "video_count", "revision_count", "delivery_days", "featured", "published")}


def accessible_request(db: Session, actor: User, request_id: int) -> Request:
    item = db.get(Request, request_id)
    if not item or (actor.role != "admin" and actor.id not in {item.teacher_id, item.designer_id}):
        raise HTTPException(404, "الطلب غير موجود")
    return item


def count_slots(db: Session, teacher: User, kind: str) -> dict:
    reserved = db.scalar(select(func.count()).select_from(Request).where(Request.teacher_id == teacher.id, Request.kind == kind, Request.status.in_(["accepted", "in_progress"]))) or 0
    completed = db.scalar(select(func.count()).select_from(Request).where(Request.teacher_id == teacher.id, Request.kind == kind, Request.status.in_(["completed", "revision_requested"]))) or 0
    total = teacher.image_limit if kind == "image" else teacher.video_limit
    return {"total": total, "reserved": reserved, "completed": completed, "available": max(0, total - reserved - completed)}


app = FastAPI(title="Fhmny Creative Desk", version="0.1.0")
origins = [value.strip() for value in os.getenv("DESK_CORS_ORIGINS", "http://localhost:5173").split(",") if value.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])


@app.on_event("startup")
def create_tables():
    if not IS_PRODUCTION:
        Base.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/v1/desk/public/teachers")
def public_teachers(db: Db):
    return [public_teacher_out(item) for item in db.scalars(select(PublicTeacher).where(PublicTeacher.published.is_(True)).order_by(PublicTeacher.name)).all()]


@app.get("/api/v1/desk/public/teachers/{slug}")
def public_teacher(slug: str, db: Db):
    teacher = db.scalar(select(PublicTeacher).where(PublicTeacher.slug == slug, PublicTeacher.published.is_(True)))
    if not teacher:
        raise HTTPException(404, "صفحة المدرس غير موجودة")
    works = db.scalars(select(PublicWork).where(PublicWork.teacher_id == teacher.id, PublicWork.published.is_(True)).order_by(PublicWork.id.desc())).all()
    return {**public_teacher_out(teacher), "works": [public_work_out(item) for item in works]}


@app.get("/api/v1/desk/public/work")
def public_work(db: Db):
    items = db.scalars(select(PublicWork).outerjoin(PublicTeacher, PublicWork.teacher_id == PublicTeacher.id).where(PublicWork.published.is_(True), (PublicWork.teacher_id.is_(None)) | (PublicTeacher.published.is_(True))).order_by(PublicWork.id.desc()).limit(60)).all()
    return [public_work_out(item) for item in items]


@app.get("/api/v1/desk/public/packages")
def public_packages(db: Db):
    items = db.scalars(select(PublicPackage).where(PublicPackage.published.is_(True)).order_by(PublicPackage.featured.desc(), PublicPackage.price_egp)).all()
    return [public_package_out(item) for item in items]


@app.get("/api/v1/desk/admin/public/teachers")
def admin_public_teachers(actor: Actor, db: Db):
    require_role(actor, "admin")
    return [public_teacher_out(item) for item in db.scalars(select(PublicTeacher).order_by(PublicTeacher.id.desc())).all()]


@app.post("/api/v1/desk/admin/public/teachers", status_code=201)
def create_public_teacher(data: PublicTeacherIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    if db.scalar(select(PublicTeacher.id).where(PublicTeacher.slug == data.slug)):
        raise HTTPException(409, "رابط صفحة المدرس مستخدم بالفعل")
    teacher = PublicTeacher(**data.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return public_teacher_out(teacher)


@app.patch("/api/v1/desk/admin/public/teachers/{teacher_id}")
def update_public_teacher(teacher_id: int, data: PublicTeacherIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    teacher = db.get(PublicTeacher, teacher_id)
    if not teacher:
        raise HTTPException(404, "صفحة المدرس غير موجودة")
    existing = db.scalar(select(PublicTeacher.id).where(PublicTeacher.slug == data.slug, PublicTeacher.id != teacher_id))
    if existing:
        raise HTTPException(409, "رابط صفحة المدرس مستخدم بالفعل")
    for key, value in data.model_dump().items():
        setattr(teacher, key, value)
    db.commit()
    return public_teacher_out(teacher)


@app.get("/api/v1/desk/admin/public/work")
def admin_public_work(actor: Actor, db: Db):
    require_role(actor, "admin")
    return [public_work_out(item) for item in db.scalars(select(PublicWork).order_by(PublicWork.id.desc())).all()]


@app.post("/api/v1/desk/admin/public/work", status_code=201)
def create_public_work(data: PublicWorkIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    if data.teacher_id is not None and not db.get(PublicTeacher, data.teacher_id):
        raise HTTPException(422, "صفحة المدرس غير موجودة")
    item = PublicWork(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return public_work_out(item)


@app.patch("/api/v1/desk/admin/public/work/{work_id}")
def update_public_work(work_id: int, data: PublicWorkIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    item = db.get(PublicWork, work_id)
    if not item:
        raise HTTPException(404, "العمل غير موجود")
    if data.teacher_id is not None and not db.get(PublicTeacher, data.teacher_id):
        raise HTTPException(422, "صفحة المدرس غير موجودة")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return public_work_out(item)


@app.get("/api/v1/desk/admin/public/packages")
def admin_public_packages(actor: Actor, db: Db):
    require_role(actor, "admin")
    return [public_package_out(item) for item in db.scalars(select(PublicPackage).order_by(PublicPackage.id.desc())).all()]


@app.post("/api/v1/desk/admin/public/packages", status_code=201)
def create_public_package(data: PublicPackageIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    item = PublicPackage(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return public_package_out(item)


@app.patch("/api/v1/desk/admin/public/packages/{package_id}")
def update_public_package(package_id: int, data: PublicPackageIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    item = db.get(PublicPackage, package_id)
    if not item:
        raise HTTPException(404, "الباقة غير موجودة")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return public_package_out(item)


@app.post("/api/v1/desk/setup", status_code=201)
def setup_admin(data: UserIn, db: Db, x_setup_key: Annotated[str | None, Header()] = None):
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(403, "تم إعداد النظام بالفعل")
    setup_key = os.getenv("DESK_SETUP_KEY", "")
    if data.role != Role.admin or not setup_key or not x_setup_key or not secrets.compare_digest(x_setup_key, setup_key):
        raise HTTPException(403, "الإعداد غير متاح")
    user = User(name=data.name, email=data.email.lower(), password_hash=hash_password(data.password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@app.post("/api/v1/desk/login")
def login(data: LoginIn, db: Db):
    attempt_key = hashlib.sha256(data.email.lower().encode()).hexdigest()
    attempt = db.get(LoginAttempt, attempt_key)
    if attempt and attempt.blocked_until and attempt.blocked_until.replace(tzinfo=timezone.utc) > now():
        raise HTTPException(429, "محاولات دخول كثيرة؛ جرّب بعد 15 دقيقة")
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not user.active or not check_password(data.password, user.password_hash):
        if not attempt:
            attempt = LoginAttempt(key=attempt_key, attempts=0)
            db.add(attempt)
        attempt.attempts += 1
        if attempt.attempts >= 5:
            attempt.blocked_until = now() + timedelta(minutes=15)
            attempt.attempts = 0
        db.commit()
        raise HTTPException(401, "البريد أو كلمة المرور غير صحيحة")
    if attempt:
        db.delete(attempt)
    token = secrets.token_urlsafe(40)
    db.add(LoginSession(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=now() + timedelta(days=7)))
    db.commit()
    return {"token": token, "user": user_out(user)}


@app.post("/api/v1/desk/logout", status_code=204)
def logout(actor: Actor, db: Db, authorization: Annotated[str, Header()]):
    token_hash = hashlib.sha256(authorization.removeprefix("Bearer ").strip().encode()).hexdigest()
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_hash, LoginSession.user_id == actor.id))
    if session:
        db.delete(session)
        db.commit()


@app.post("/api/v1/desk/change-password", status_code=204)
def change_password(data: ChangePasswordIn, actor: Actor, db: Db):
    if not check_password(data.current_password, actor.password_hash):
        raise HTTPException(403, "كلمة المرور الحالية غير صحيحة")
    actor.password_hash = hash_password(data.new_password)
    for session in db.scalars(select(LoginSession).where(LoginSession.user_id == actor.id)).all():
        db.delete(session)
    db.commit()


@app.post("/api/v1/desk/admin/users/{user_id}/reset-password", status_code=204)
def admin_reset_password(user_id: int, data: AdminResetPasswordIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    user = db.get(User, user_id)
    if not user or user.role == "admin":
        raise HTTPException(404, "الحساب غير موجود")
    user.password_hash = hash_password(data.new_password)
    for session in db.scalars(select(LoginSession).where(LoginSession.user_id == user.id)).all():
        db.delete(session)
    db.add(Audit(actor_id=actor.id, action="password_reset", detail=f"user={user.id}"))
    db.commit()


@app.get("/api/v1/desk/me")
def me(actor: Actor, db: Db):
    data = user_out(actor)
    if actor.role == "teacher":
        data["quotas"] = {kind: count_slots(db, actor, kind) for kind in ("image", "video")}
    return data


@app.get("/api/v1/desk/users")
def list_users(actor: Actor, db: Db):
    require_role(actor, "admin")
    result = []
    for user in db.scalars(select(User).order_by(User.name)).all():
        row = user_out(user)
        if user.role == "teacher":
            row["quotas"] = {kind: count_slots(db, user, kind) for kind in ("image", "video")}
        result.append(row)
    return result


@app.get("/api/v1/desk/admin/audit")
def audit_events(actor: Actor, db: Db, offset: int = 0, limit: int = 50):
    require_role(actor, "admin")
    events = db.scalars(select(Audit).order_by(Audit.id.desc()).offset(max(0, offset)).limit(min(100, max(1, limit)))).all()
    return [{"id": event.id, "actor_id": event.actor_id, "request_id": event.request_id, "action": event.action, "detail": event.detail, "created_at": event.created_at} for event in events]


@app.post("/api/v1/desk/users", status_code=201)
def create_user(data: UserIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    if data.role == Role.admin:
        raise HTTPException(403, "لا يمكن إنشاء أدمن من هذه الواجهة")
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "البريد مستخدم بالفعل")
    user = User(**data.model_dump(exclude={"password", "role", "email"}), email=data.email.lower(), role=data.role.value, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@app.patch("/api/v1/desk/users/{user_id}/active")
def set_active(user_id: int, active: bool, actor: Actor, db: Db):
    require_role(actor, "admin")
    user = db.get(User, user_id)
    if not user or user.role == "admin":
        raise HTTPException(404, "الحساب غير موجود")
    user.active = active
    db.commit()
    return user_out(user)


@app.patch("/api/v1/desk/teachers/{teacher_id}/assignment")
def assign_teacher(teacher_id: int, data: AssignmentIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    teacher, designer = db.get(User, teacher_id, with_for_update=True), db.get(User, data.designer_id)
    if not teacher or teacher.role != "teacher" or not designer or designer.role != "designer" or not designer.active:
        raise HTTPException(422, "المدرس أو المصمم غير صالح")
    for kind, total in (("image", data.image_limit), ("video", data.video_limit)):
        slots = count_slots(db, teacher, kind)
        if total < slots["reserved"] + slots["completed"]:
            raise HTTPException(409, f"لا يمكن تقليل رصيد {kind} أقل من المستخدم")
    teacher.designer_id = designer.id
    teacher.image_limit, teacher.video_limit = data.image_limit, data.video_limit
    # Access to every existing request follows the teacher's current designer.
    # Keep request history, messages and links while revoking the old designer.
    db.execute(update(Request).where(Request.teacher_id == teacher.id).values(designer_id=designer.id, updated_at=now()))
    db.add(Audit(actor_id=actor.id, action="assignment_updated", detail=f"teacher={teacher.id},designer={designer.id},image={data.image_limit},video={data.video_limit}"))
    db.commit()
    return user_out(teacher)


@app.get("/api/v1/desk/requests")
def list_requests(actor: Actor, db: Db, offset: int = 0, limit: int = 50):
    query = select(Request)
    if actor.role == "teacher":
        query = query.where(Request.teacher_id == actor.id)
    elif actor.role == "designer":
        query = query.where(Request.designer_id == actor.id)
    return [request_out(item) for item in db.scalars(query.order_by(Request.updated_at.desc()).offset(max(0, offset)).limit(min(100, max(1, limit)))).all()]


@app.post("/api/v1/desk/requests", status_code=201)
def create_request(data: RequestIn, actor: Actor, db: Db):
    require_role(actor, "teacher")
    if not actor.designer_id:
        raise HTTPException(409, "الأدمن لم يحدد مصممًا بعد")
    designer = db.get(User, actor.designer_id)
    if not designer or not designer.active:
        raise HTTPException(409, "المصمم غير متاح الآن")
    item = Request(teacher_id=actor.id, designer_id=designer.id, kind=data.kind, title=data.title, brief=data.brief)
    db.add(item)
    db.flush()
    for url in data.references:
        db.add(Link(request_id=item.id, author_id=actor.id, url=url, label=urlparse(url).hostname or "مرجع", kind="reference"))
    db.add(Audit(actor_id=actor.id, request_id=item.id, action="created"))
    db.commit()
    db.refresh(item)
    return request_out(item)


@app.get("/api/v1/desk/requests/{request_id}")
def get_request(request_id: int, actor: Actor, db: Db):
    item = accessible_request(db, actor, request_id)
    messages = db.scalars(select(Message).where(Message.request_id == item.id).order_by(Message.id)).all()
    links = db.scalars(select(Link).where(Link.request_id == item.id).order_by(Link.id)).all()
    teacher = db.get(User, item.teacher_id)
    profile = {key: getattr(teacher, key) for key in ("name", "subject", "facebook", "tiktok", "youtube")} if teacher else None
    return {**request_out(item), "teacher_profile": profile, "messages": [{"id": m.id, "author_id": m.author_id, "body": m.body, "created_at": m.created_at} for m in messages], "links": [{"id": link.id, "author_id": link.author_id, "url": link.url, "label": link.label, "kind": link.kind, "created_at": link.created_at} for link in links]}


@app.post("/api/v1/desk/requests/{request_id}/messages", status_code=201)
def add_message(request_id: int, data: MessageIn, actor: Actor, db: Db):
    item = accessible_request(db, actor, request_id)
    message = Message(request_id=item.id, author_id=actor.id, body=data.body.strip())
    db.add(message)
    item.updated_at = now()
    db.commit()
    db.refresh(message)
    return {"id": message.id, "author_id": actor.id, "body": message.body, "created_at": message.created_at}


@app.post("/api/v1/desk/requests/{request_id}/links", status_code=201)
def add_link(request_id: int, data: LinkIn, actor: Actor, db: Db):
    item = accessible_request(db, actor, request_id)
    require_role(actor, "designer")
    if item.status not in {"accepted", "in_progress", "revision_requested"}:
        raise HTTPException(409, "اقبل الطلب قبل التسليم")
    link = Link(request_id=item.id, author_id=actor.id, url=data.url, label=data.label, kind=data.kind)
    db.add(link)
    if item.status != "revision_requested":
        item.status = "in_progress"
    item.updated_at = now()
    db.commit()
    db.refresh(link)
    return {"id": link.id, "url": link.url, "label": link.label, "kind": link.kind}


@app.post("/api/v1/desk/requests/{request_id}/{action}")
def transition(request_id: int, action: str, actor: Actor, db: Db):
    item = accessible_request(db, actor, request_id)
    allowed = {
        "accept": ({"submitted"}, {"designer", "admin"}, "accepted"),
        "deliver": ({"accepted", "in_progress", "revision_requested"}, {"designer"}, "completed"),
        "revise": ({"completed"}, {"teacher"}, "revision_requested"),
        "cancel": ({"submitted"}, {"teacher", "admin"}, "canceled"),
    }
    if action not in allowed:
        raise HTTPException(404, "الإجراء غير موجود")
    states, roles, target = allowed[action]
    if item.status not in states or actor.role not in roles:
        raise HTTPException(409, "الإجراء غير متاح في هذه المرحلة")
    if action == "accept":
        teacher = db.get(User, item.teacher_id, with_for_update=True)
        if count_slots(db, teacher, item.kind)["available"] < 1:
            raise HTTPException(409, "الرصيد غير كافٍ")
    if action == "deliver" and not db.scalar(select(Link.id).where(Link.request_id == item.id, Link.kind == "final")):
        raise HTTPException(409, "أضف رابط Drive النهائي أولًا")
    item.status = target
    item.updated_at = now()
    db.add(Audit(actor_id=actor.id, request_id=item.id, action=action))
    db.commit()
    return request_out(item)


@app.post("/api/v1/desk/admin/requests/{request_id}/cancel")
def admin_cancel(request_id: int, data: ReasonIn, actor: Actor, db: Db):
    require_role(actor, "admin")
    item = accessible_request(db, actor, request_id)
    if item.status in {"completed", "canceled"}:
        raise HTTPException(409, "الطلب مغلق")
    item.status = "canceled"
    item.updated_at = now()
    db.add(Audit(actor_id=actor.id, request_id=item.id, action="admin_cancel", detail=data.reason))
    db.commit()
    return request_out(item)


static_dir = os.getenv("DESK_STATIC_DIR")
if static_dir:
    path = Path(static_dir).resolve()
    if not (path / "index.html").is_file():
        raise RuntimeError("DESK_STATIC_DIR must contain index.html")
    app.mount("/", StaticFiles(directory=str(path), html=True), name="desk-web")
