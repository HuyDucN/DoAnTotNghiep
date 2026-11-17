"""Muc 4: thong bao ung vien moi, nhan ban job, xuat CSV."""
from datetime import datetime, timedelta
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
from app.models import audit_log, cv, profile, skill, skill_gap
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import Skill
from app.models.skill_gap import SkillGap
from app.models.user import User


@pytest.fixture
def ops_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)
    now = datetime.now().replace(microsecond=0)
    with maker() as s:
        s.add_all([
            User(id=1, email="admin@x.test", full_name="Admin", password_hash="h", role="admin"),
            User(id=2, email="rec@x.test", full_name="Rec", password_hash="h", role="recruiter",
                 is_verified=True),
            User(id=3, email="rec2@x.test", full_name="Rec2", password_hash="h", role="recruiter",
                 is_verified=True),
            User(id=4, email="cand@x.test", full_name="Cand", password_hash="h", role="user"),
            User(id=5, email="user@x.test", full_name="U", password_hash="h", role="user"),
        ])
        s.add_all([
            Job(id=1, title="Own", owner_id=2),
            Job(id=2, title="Other", owner_id=3),
        ])
        s.add(Skill(id=1, name="Python", normalized_name="python"))
        s.add(JobSkill(job_id=1, skill_id=1, is_required=True, importance="high"))
        s.add(CV(id=1, user_id=4, filename="a.pdf", file_path="/tmp/a.pdf", status="analyzed"))
        s.add(CV(id=2, user_id=4, filename="b.pdf", file_path="/tmp/b.pdf", status="analyzed"))
        s.add(CV(id=3, user_id=4, filename="c.pdf", file_path="/tmp/c.pdf", status="analyzed"))
        s.add_all([
            SkillGap(id=1, user_id=4, cv_id=1, job_id=1, match_score=80,
                     matched_skills=[], missing_skills=[], weak_skills=[],
                     review_status="new", matched_at=now),
            SkillGap(id=2, user_id=4, cv_id=2, job_id=1, match_score=70,
                     matched_skills=[], missing_skills=[], weak_skills=[],
                     review_status="viewed", matched_at=now),
            SkillGap(id=3, user_id=4, cv_id=1, job_id=2, match_score=60,
                     matched_skills=[], missing_skills=[], weak_skills=[],
                     review_status="new", matched_at=now),
            SkillGap(id=4, user_id=4, cv_id=3, job_id=1, match_score=50,
                     matched_skills=[], missing_skills=[], weak_skills=[],
                     review_status="new", matched_at=now - timedelta(days=30)),
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
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**role)
    try:
        with TestClient(app) as client:
            yield client, role
    finally:
        engine.dispose()


def test_new_applicant_notices_scoped_to_owner(ops_api):
    client, role = ops_api
    data = client.get("/api/jobs/admin/notifications/new-applicants").json()
    # Gap 1 (new, recent, own job); gap 4 qua cu (30 ngay); gap 3 job khac; gap 2 da viewed.
    assert [n["id"] for n in data] == [1]
    assert data[0]["job_id"] == 1 and data[0]["job_title"] == "Own"
    role.update(id=1, role="admin")
    assert {n["id"] for n in client.get("/api/jobs/admin/notifications/new-applicants").json()} == {1, 3}


def test_duplicate_job_copies_skills(ops_api):
    client, role = ops_api
    r = client.post("/api/jobs/admin/1/duplicate")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Own (bản sao)"
    assert data["is_active"] is False
    assert data["owner_id"] == 2
    assert len(data["job_skills"]) == 1
    assert client.post("/api/jobs/admin/2/duplicate").status_code == 403
    role.update(id=1, role="admin")
    assert client.post("/api/jobs/admin/2/duplicate").status_code == 201


def test_export_applicants_csv(ops_api):
    client, role = ops_api
    r = client.get("/api/jobs/admin/1/applicants/export")
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.lstrip("﻿").strip().splitlines()
    assert lines[0] == "id,candidate_name,candidate_email,cv_filename,match_score,review_status,recruiter_note,matched_at"
    assert len(lines) == 4  # header + 3 gaps cua job 1
    filtered = client.get("/api/jobs/admin/1/applicants/export", params={"review_status": "new"})
    assert len(filtered.text.strip().splitlines()) == 3  # header + gap 1, 4
    assert client.get("/api/jobs/admin/2/applicants/export").status_code == 403
    role.update(id=5, role="user")
    assert client.get("/api/jobs/admin/1/applicants/export").status_code == 403
