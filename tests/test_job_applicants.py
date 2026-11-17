"""Recruiter xem va cap nhat pipeline ung vien cho job cua ho."""
from datetime import datetime
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
from app.models import cv, profile, skill, user
from app.models.cv import CV
from app.models.job import Job
from app.models.skill_gap import SkillGap
from app.models.user import User


@pytest.fixture
def applicants_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)()
    sessions.add_all([
        User(id=1, email="admin@x.test", full_name="Admin", password_hash="h", role="admin"),
        User(id=2, email="rec@x.test", full_name="Rec", password_hash="h", role="recruiter"),
        User(id=3, email="rec2@x.test", full_name="Rec2", password_hash="h", role="recruiter"),
        User(id=4, email="cand@x.test", full_name="Cand", password_hash="h", role="user"),
        User(id=5, email="user@x.test", full_name="U", password_hash="h", role="user"),
    ])
    sessions.add_all([
        Job(id=1, title="Own", owner_id=2),
        Job(id=2, title="Other", owner_id=3),
    ])
    sessions.add_all([
        CV(id=1, user_id=4, filename="a.pdf", file_path="/tmp/a.pdf", status="analyzed"),
        CV(id=2, user_id=4, filename="b.pdf", file_path="/tmp/b.pdf", status="analyzed"),
    ])
    sessions.add_all([
        SkillGap(id=1, user_id=4, cv_id=1, job_id=1, match_score=80,
                 matched_skills=[], missing_skills=[], weak_skills=[],
                 matched_at=datetime(2026, 10, 2)),
        SkillGap(id=2, user_id=4, cv_id=2, job_id=2, match_score=70,
                 matched_skills=[], missing_skills=[], weak_skills=[],
                 matched_at=datetime(2026, 10, 3)),
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


def test_recruiter_lists_only_own_job_applicants(applicants_api):
    client, _ = applicants_api
    data = client.get("/api/jobs/admin/1/applicants").json()
    assert [a["id"] for a in data["items"]] == [1]
    assert data["items"][0]["candidate_email"] == "cand@x.test"
    assert data["items"][0]["review_status"] == "new"
    assert client.get("/api/jobs/admin/2/applicants").status_code == 403


def test_recruiter_reviews_applicant(applicants_api):
    client, _ = applicants_api
    r = client.patch("/api/jobs/admin/applicants/1",
                     json={"review_status": "shortlisted", "recruiter_note": "Hop React"})
    assert r.status_code == 200, r.text
    assert r.json()["review_status"] == "shortlisted"
    assert r.json()["recruiter_note"] == "Hop React"
    assert r.json()["reviewed_at"] is not None
    filtered = client.get("/api/jobs/admin/1/applicants", params={"review_status": "new"}).json()
    assert filtered["total"] == 0


def test_recruiter_cannot_review_other_job_applicant(applicants_api):
    client, _ = applicants_api
    assert client.patch("/api/jobs/admin/applicants/2",
                        json={"review_status": "hired"}).status_code == 403


def test_admin_can_review_any_applicant(applicants_api):
    client, role = applicants_api
    role.update(role="admin", id=1)
    r = client.patch("/api/jobs/admin/applicants/2", json={"review_status": "viewed"})
    assert r.status_code == 200, r.text


def test_user_cannot_access_applicants(applicants_api):
    client, role = applicants_api
    role.update(role="user", id=5)
    assert client.get("/api/jobs/admin/1/applicants").status_code == 403
    assert client.patch("/api/jobs/admin/applicants/1",
                        json={"review_status": "viewed"}).status_code == 403
