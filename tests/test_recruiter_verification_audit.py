"""Recruiter cho duyet moi duoc dang job; audit log ghi hanh dong quan tri."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.api.auth import register
from app.api.jobs import router as jobs_router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import audit_log, cv, job, profile, skill, skill_gap
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.user import UserCreate


@pytest.fixture
def verification_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)
    with maker() as session:
        session.add_all([
            User(id=1, email="admin@x.test", full_name="Admin",
                 password_hash="h", role="admin", is_active=True, is_verified=True),
            User(id=2, email="rec@x.test", full_name="Rec",
                 password_hash="h", role="recruiter", is_active=True, is_verified=False),
        ])
        session.commit()
    role = {"id": 1, "role": "admin"}

    def test_db():
        with maker() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app = FastAPI()
    app.include_router(admin_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**role)
    try:
        with TestClient(app) as client:
            yield client, role, maker
    finally:
        engine.dispose()


def test_register_recruiter_is_unverified(verification_api):
    _, _, maker = verification_api
    with maker() as db:
        result = register(UserCreate(email="new-rec@example.com", password="password123",
                                     full_name="New Rec", role="recruiter"), db=db,
                          _=None)
        assert result.user.role == "recruiter"
        assert result.user.is_verified is False
    with maker() as db:
        result = register(UserCreate(email="new-user@example.com", password="password123",
                                     full_name="New User"), db=db,
                          _=None)
        assert result.user.role == "user"
        assert result.user.is_verified is True


def test_unverified_recruiter_cannot_manage_jobs(verification_api):
    client, role, _ = verification_api
    role.update(id=2, role="recruiter", is_verified=False)
    assert client.get("/api/jobs/admin/list").status_code == 403
    assert client.post("/api/jobs/admin", json={"title": "X"}).status_code == 403


def test_admin_verify_enables_recruiter_and_logs_audit(verification_api):
    client, role, maker = verification_api
    r = client.patch("/api/admin/users/2/verify", json={"is_verified": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_verified"] is True
    # Duyet lam tang token_version -> JWT cu khong dung lai duoc.
    with maker() as db:
        assert db.get(User, 2).token_version == 1

    role.update(id=2, role="recruiter")
    assert client.get("/api/jobs/admin/list").status_code == 200
    with maker() as db:
        entries = db.query(AuditLog).filter(AuditLog.action == "recruiter.verify").all()
    assert len(entries) == 1
    assert entries[0].target_id == 2


def test_verify_rejects_non_recruiter(verification_api):
    client, _, _ = verification_api
    assert client.patch("/api/admin/users/1/verify", json={"is_verified": True}).status_code == 400


def test_audit_logs_require_admin(verification_api):
    client, role, _ = verification_api
    role.update(id=2, role="recruiter")
    assert client.get("/api/admin/audit-logs").status_code == 403
