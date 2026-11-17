"""Thong ke job (recruiter), overview he thong (admin)."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.api.jobs import router as jobs_router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import audit_log, cv, job, profile, skill, skill_gap
from app.models.cv import CV
from app.models.job import Job
from app.models.skill_gap import SkillGap
from app.models.user import User


@pytest.fixture
def stats_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)
    with maker() as s:
        s.add_all([
            User(id=1, email="admin@x.test", full_name="Admin", password_hash="h", role="admin"),
            User(id=2, email="rec@x.test", full_name="Rec", password_hash="h", role="recruiter",
                 is_verified=True),
            User(id=3, email="rec2@x.test", full_name="Rec2", password_hash="h", role="recruiter",
                 is_verified=True),
            User(id=4, email="cand@x.test", full_name="Cand", password_hash="h", role="user"),
        ])
        s.add_all([
            Job(id=1, title="Own", owner_id=2),
            Job(id=2, title="Other", owner_id=3),
        ])
        s.add_all([
            CV(id=1, user_id=4, filename="a.pdf", file_path="/tmp/a.pdf", status="analyzed"),
            CV(id=2, user_id=4, filename="b.pdf", file_path="/tmp/b.pdf", status="analyzed"),
        ])
        now = datetime.now().replace(microsecond=0)
        s.add_all([
            SkillGap(id=1, user_id=4, cv_id=1, job_id=1, match_score=80,
                     matched_skills=[], missing_skills=[{"skill_name": "Docker"}],
                     weak_skills=[{"skill_name": "Python"}], review_status="new",
                     matched_at=now),
            SkillGap(id=2, user_id=4, cv_id=2, job_id=1, match_score=60,
                     matched_skills=[], missing_skills=[{"skill_name": "Docker"}],
                     weak_skills=[], review_status="shortlisted", matched_at=now),
            SkillGap(id=3, user_id=4, cv_id=1, job_id=2, match_score=30,
                     matched_skills=[], missing_skills=[{"skill_name": "K8s"}],
                     weak_skills=[], review_status="new", matched_at=now),
        ])
        s.commit()
    role = {"id": 2, "role": "recruiter", "is_verified": True}

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
            yield client, role
    finally:
        engine.dispose()


def test_recruiter_gets_own_job_stats(stats_api):
    client, _ = stats_api
    r = client.get("/api/jobs/admin/1/stats")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_applicants"] == 2
    assert data["avg_score"] == 70.0
    assert data["review_status_counts"]["new"] == 1
    assert data["review_status_counts"]["shortlisted"] == 1
    assert data["score_buckets"]["75-100"] == 1
    assert data["score_buckets"]["50-74"] == 1
    assert data["top_missing_skills"] == [{"skill_name": "Docker", "count": 2}]
    assert client.get("/api/jobs/admin/2/stats").status_code == 403


def test_recruiter_overview_mine(stats_api):
    client, _ = stats_api
    r = client.get("/api/jobs/admin-overview/mine")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_jobs"] == 1
    assert data["total_applicants"] == 2
    assert data["pending_review"] == 1
    assert data["recent_jobs"][0]["id"] == 1


def test_admin_stats_overview(stats_api):
    client, role = stats_api
    role.update(id=1, role="admin")
    r = client.get("/api/admin/stats")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["totals"] == {"users": 4, "active_users": 4, "jobs": 2,
                              "active_jobs": 2, "cvs": 2, "matches": 3}
    assert data["users_by_role"]["recruiter"] == 2
    assert data["matches_by_review_status"]["new"] == 2
    assert data["top_missing_skills"][0] == {"skill_name": "Docker", "count": 2}
    assert {r["id"] for r in data["top_recruiters"]} == {2, 3}


def test_stats_require_privileged_role(stats_api):
    client, role = stats_api
    role.update(id=4, role="user")
    assert client.get("/api/jobs/admin/1/stats").status_code == 403
    assert client.get("/api/jobs/admin-overview/mine").status_code == 403
    assert client.get("/api/admin/stats").status_code == 403
