"""Kiểm tra cập nhật từng phần của Job qua API và database độc lập."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.jobs import router
from app.api import jobs as jobs_api
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import cv, profile, skill_gap, user
from app.models.job import Job, JobSkill
from app.models.skill import Skill


@pytest.fixture
def job_update_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    session.add_all([
        Skill(id=1, name="Python", normalized_name="python"),
        Skill(id=2, name="Docker", normalized_name="docker"),
        Skill(id=3, name="SQL", normalized_name="sql"),
        Job(
            id=1, title="Backend Developer", company="Example", location="Hà Nội",
            level="senior", category="backend", job_type="part_time",
            description="Mô tả cũ", salary_min=1000, salary_max=2000,
        ),
        Job(id=2, title="Other Job"),
    ])
    session.flush()
    session.add_all([
        JobSkill(job_id=1, skill_id=1, is_required=True, importance="high"),
        JobSkill(job_id=1, skill_id=2, is_required=False, importance="low"),
        JobSkill(job_id=2, skill_id=1, is_required=True, importance="medium"),
    ])
    session.commit()

    def test_db():
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="admin")
    try:
        with TestClient(app) as client:
            yield client, session, app
    finally:
        session.close()
        engine.dispose()


def skill_rows(session, job_id=1):
    return sorted(
        (row.skill_id, row.is_required, row.importance)
        for row in session.query(JobSkill).filter(JobSkill.job_id == job_id).all()
    )


@pytest.mark.parametrize("payload", [{"title": "New Title"}, {"salary_min": 1200}, {}])
def test_partial_update_preserves_omitted_fields_and_skills(job_update_api, payload):
    client, session, _ = job_update_api
    before = skill_rows(session)
    response = client.put("/api/jobs/admin/1", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["title"] == payload.get("title", "Backend Developer")
    assert result["salary_min"] == payload.get("salary_min", 1000)
    assert result["salary_max"] == 2000
    assert (result["level"], result["category"], result["job_type"]) == (
        "senior", "backend", "part_time",
    )
    assert skill_rows(session) == before
    assert len(result["job_skills"]) == 2


@pytest.mark.parametrize("field,is_required", [("required_skills", True), ("preferred_skills", False)])
def test_update_replaces_only_the_supplied_skill_group(job_update_api, field, is_required):
    client, session, _ = job_update_api
    response = client.put("/api/jobs/admin/1", json={
        field: [{"skill_name": "SQL", "importance": "medium"}],
    })
    assert response.status_code == 200, response.text
    unchanged = (2, False, "low") if is_required else (1, True, "high")
    assert skill_rows(session) == sorted([unchanged, (3, is_required, "medium")])
    assert skill_rows(session, job_id=2) == [(1, True, "medium")]
    assert {item["skill_name"] for item in response.json()["job_skills"]} == (
        {"SQL", "Docker"} if is_required else {"SQL", "Python"}
    )


@pytest.mark.parametrize("payload,expected", [
    ({"required_skills": []}, [(2, False, "low")]),
    ({"preferred_skills": []}, [(1, True, "high")]),
    ({"required_skills": [], "preferred_skills": []}, []),
])
def test_explicit_empty_list_clears_only_the_supplied_group(job_update_api, payload, expected):
    client, session, _ = job_update_api
    response = client.put("/api/jobs/admin/1", json=payload)
    assert response.status_code == 200, response.text
    assert skill_rows(session) == expected
    assert len(response.json()["job_skills"]) == len(expected)
    assert session.query(Skill).count() == 3


def test_full_admin_form_can_clear_nullable_fields_and_replace_both_groups(job_update_api):
    client, session, _ = job_update_api
    response = client.put("/api/jobs/admin/1", json={
        "title": "Updated Job", "company": None, "location": None,
        "description": None, "salary_min": None, "salary_max": None,
        "job_type": "full_time", "level": "junior", "category": "data",
        "required_skills": [{"skill_name": "SQL", "importance": "high"}],
        "preferred_skills": [{"skill_name": "Python", "importance": "low"}],
    })
    assert response.status_code == 200, response.text
    result = response.json()
    for field in ("company", "location", "description", "salary_min", "salary_max"):
        assert result[field] is None
    assert result["title"] == "Updated Job"
    assert skill_rows(session) == [(1, False, "low"), (3, True, "high")]


@pytest.mark.parametrize("field", [
    "title", "job_type", "level", "category", "required_skills", "preferred_skills",
])
def test_null_is_rejected_for_fields_that_cannot_be_cleared(job_update_api, field):
    client, session, _ = job_update_api
    before = skill_rows(session)
    response = client.put("/api/jobs/admin/1", json={field: None, "company": "Changed"})
    assert response.status_code == 422, response.text
    assert session.get(Job, 1).company == "Example"
    assert skill_rows(session) == before


def test_update_of_missing_job_returns_404(job_update_api):
    client, _, _ = job_update_api
    assert client.put("/api/jobs/admin/999", json={"title": "New"}).status_code == 404


def test_regular_user_cannot_update_job(job_update_api):
    client, session, app = job_update_api
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role="user")
    response = client.put("/api/jobs/admin/1", json={"title": "New"})
    assert response.status_code == 403
    assert session.get(Job, 1).title == "Backend Developer"


def test_failure_while_replacing_skills_rolls_back_the_whole_update(job_update_api, monkeypatch):
    client, session, _ = job_update_api
    before = skill_rows(session)
    original_helper = jobs_api._get_or_restore_skill

    def fail_on_preferred_skill(db, normalized, display_name):
        if normalized == "docker":
            raise IntegrityError("insert", {}, RuntimeError("simulated database conflict"))
        return original_helper(db, normalized, display_name)

    monkeypatch.setattr(jobs_api, "_get_or_restore_skill", fail_on_preferred_skill)
    with pytest.raises(IntegrityError):
        client.put("/api/jobs/admin/1", json={
            "title": "Should roll back",
            "required_skills": [{"skill_name": "SQL"}],
            "preferred_skills": [{"skill_name": "Docker"}],
        })
    assert session.get(Job, 1).title == "Backend Developer"
    assert skill_rows(session) == before
    assert skill_rows(session, job_id=2) == [(1, True, "medium")]
