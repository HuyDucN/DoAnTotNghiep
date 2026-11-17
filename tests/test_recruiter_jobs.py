"""Recruiter chỉ CRUD job của họ; admin giữ toàn quyền; user bị chặn."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.jobs import router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import cv, profile, skill, skill_gap, user
from app.models.job import Job
from app.models.user import User


@pytest.fixture
def recruiter_jobs_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)()
    sessions.add_all([
        User(id=1, email="admin@x.test", full_name="Admin", password_hash="h", role="admin"),
        User(id=2, email="rec@x.test", full_name="Rec", password_hash="h", role="recruiter"),
        User(id=3, email="rec2@x.test", full_name="Rec2", password_hash="h", role="recruiter"),
        User(id=4, email="user@x.test", full_name="User", password_hash="h", role="user"),
    ])
    sessions.add_all([
        Job(id=1, title="Own Job", company="A", owner_id=2),
        Job(id=2, title="Other Job", company="B", owner_id=3),
        Job(id=3, title="Legacy Job", company="C", owner_id=None),
    ])
    sessions.commit()
    role = {"role": "recruiter", "id": 2}

    def test_db():
        try:
            yield sessions
        except Exception:
            sessions.rollback()
            raise

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**role)
    try:
        with TestClient(app) as client:
            yield client, role
    finally:
        sessions.close()
        engine.dispose()


def test_recruiter_list_sees_only_own_jobs(recruiter_jobs_api):
    client, _ = recruiter_jobs_api
    data = client.get("/api/jobs/admin/list").json()
    assert [j["id"] for j in data["items"]] == [1]
    assert data["total"] == 1


def test_recruiter_create_tags_owner(recruiter_jobs_api):
    client, _ = recruiter_jobs_api
    r = client.post("/api/jobs/admin", json={"title": "New", "required_skills": [], "preferred_skills": []})
    assert r.status_code == 201, r.text
    assert r.json()["owner_id"] == 2


def test_recruiter_cannot_update_or_delete_others_job(recruiter_jobs_api):
    client, _ = recruiter_jobs_api
    assert client.put("/api/jobs/admin/2", json={"title": "Hijack"}).status_code == 403
    assert client.put("/api/jobs/admin/3", json={"title": "Hijack"}).status_code == 403
    assert client.delete("/api/jobs/admin/2").status_code == 403
    assert client.delete("/api/jobs/admin/3").status_code == 403


def test_recruiter_can_update_and_delete_own_job(recruiter_jobs_api):
    client, _ = recruiter_jobs_api
    assert client.put("/api/jobs/admin/1", json={"title": "Renamed"}).status_code == 200
    assert client.delete("/api/jobs/admin/1").status_code == 204


def test_admin_still_sees_all_jobs(recruiter_jobs_api):
    client, role = recruiter_jobs_api
    role.update(role="admin", id=1)
    data = client.get("/api/jobs/admin/list").json()
    assert data["total"] == 3


def test_user_cannot_manage_jobs(recruiter_jobs_api):
    client, role = recruiter_jobs_api
    role.update(role="user", id=4)
    assert client.get("/api/jobs/admin/list").status_code == 403
    assert client.post("/api/jobs/admin", json={"title": "X"}).status_code == 403
