"""Định danh kỹ năng phải nhất quán giữa danh mục, Job, CV và matching."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import cv as cv_api, jobs, skills
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models import profile, skill_gap
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill
from app.models.user import User
from app.services.skill_matcher import calculate_match_score


@pytest.fixture
def skill_api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    session.add(User(id=4, email="admin@example.test", full_name="Admin", password_hash="test", role="admin"))
    session.add(CV(id=27, user_id=4, filename="cv.pdf", file_path="cv.pdf", status="analyzed"))
    session.commit()

    def test_db():
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    for router in (cv_api.router, jobs.router, skills.router):
        app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4, role="admin")
    try:
        with TestClient(configure_http_errors(app, []), raise_server_exceptions=False) as client:
            yield client, session
    finally:
        session.close()
        engine.dispose()


def test_admin_catalog_keeps_symbols_and_vietnamese_names_distinct(skill_api):
    client, session = skill_api
    for name in ("C", "C++", "C#", "Kỹ năng giao tiếp"):
        response = client.post("/api/skills/", json={"name": name})
        assert response.status_code == 201, response.text
    assert {row.normalized_name for row in session.query(Skill).all()} == {
        "c", "c++", "c#", "kỹ_năng_giao_tiếp",
    }


def test_ai_job_and_manual_skill_reuse_one_identity(skill_api):
    client, session = skill_api
    created = client.post("/api/skills/", json={"name": "Machine   Learning"})
    assert created.status_code == 201, created.text
    skill_id = created.json()["id"]
    response = client.post("/api/jobs/admin", json={
        "title": "ML Developer", "level": "junior",
        "required_skills": [{"skill_name": " machine-learning "}],
    })
    assert response.status_code == 201, response.text
    assert response.json()["job_skills"][0]["skill_id"] == skill_id
    manual = client.post("/api/cv/27/skills", json={
        "skill_name": "machine_learning", "proficiency_level": "advanced", "years_experience": 3,
    })
    assert manual.status_code == 201, manual.text
    assert manual.json()["skill_id"] == skill_id
    cv_api._save_cv_skills(27, [{"name": "MACHINE  LEARNING", "proficiency_level": "beginner"}], session)
    session.commit()
    assert session.query(Skill).count() == 1
    link = session.query(CVSkill).one()
    assert (link.source, link.proficiency_level, link.years_experience) == ("manual", "advanced", 3)


def test_legacy_nodejs_is_reused_by_job_ai_and_manual_entry(skill_api):
    client, session = skill_api
    session.add(Skill(id=65, name="Node.Js", normalized_name="nodejs"))
    session.commit()
    manual = client.post("/api/cv/27/skills", json={"skill_name": "Node.js", "proficiency_level": "advanced"})
    assert manual.status_code == 201
    response = client.post("/api/jobs/admin", json={"title": "Backend", "required_skills": [{"skill_name": "node.js"}]})
    assert response.status_code == 201, response.text
    cv_api._save_cv_skills(27, [{"name": "Node.js", "proficiency_level": "beginner"}], session)
    session.commit()
    assert session.query(Skill).count() == 1
    assert session.query(CVSkill).one().source == "manual"
    assert response.json()["job_skills"][0]["skill_id"] == 65


@pytest.mark.parametrize("path,payload", [
    ("/api/skills/", {"name": "C"}),
    ("/api/jobs/admin", {"title": "C Developer", "required_skills": [{"skill_name": "C"}]}),
    ("/api/cv/27/skills", {"skill_name": "C"}),
])
def test_legacy_collision_never_relabels_cpp_as_c(skill_api, path, payload):
    client, session = skill_api
    session.add(Skill(id=65, name="C++", normalized_name="c"))
    session.commit()
    response = client.post(path, json=payload)
    assert response.status_code == 409, response.text
    assert session.get(Skill, 65).name == "C++"
    assert session.query(Job).count() == 0
    assert session.query(CVSkill).count() == 0


def test_admin_rename_cannot_collide_with_existing_skill(skill_api):
    client, session = skill_api
    first = client.post("/api/skills/", json={"name": "Python"})
    second = client.post("/api/skills/", json={"name": "Docker"})
    response = client.put(f"/api/skills/{second.json()['id']}", json={"name": " PYTHON "})
    assert response.status_code == 409, response.text
    assert session.get(Skill, second.json()["id"]).name == "Docker"
    assert session.get(Skill, first.json()["id"]).name == "Python"


def test_legacy_cpp_can_be_reused_and_restored_by_its_real_name(skill_api):
    client, session = skill_api
    session.add(Skill(id=65, name="C++", normalized_name="c", is_deleted=True))
    session.commit()
    response = client.post("/api/jobs/admin", json={
        "title": "C++ Developer", "required_skills": [{"skill_name": "C++"}],
    })
    assert response.status_code == 201, response.text
    assert response.json()["job_skills"][0]["skill_id"] == 65
    assert session.get(Skill, 65).is_deleted is False
    assert session.query(Skill).count() == 1


def test_catalog_normalizes_unicode_and_rejects_same_name_variant(skill_api):
    client, session = skill_api
    created = client.post("/api/skills/", json={"name": " Ｃ＃ "})
    assert created.status_code == 201, created.text
    assert (created.json()["name"], created.json()["normalized_name"]) == ("C#", "c#")
    duplicate = client.post("/api/skills/", json={"name": "c#"})
    assert duplicate.status_code == 400
    assert session.query(Skill).count() == 1


@pytest.mark.parametrize("is_required", [True, False])
def test_matching_does_not_confuse_legacy_cpp_with_c(skill_api, is_required):
    _, session = skill_api
    session.add_all([
        Skill(id=1, name="C++", normalized_name="c"),
        Skill(id=2, name="C", normalized_name="legacy_c"),
        Job(id=1, title="C Developer", level="junior"),
    ])
    session.flush()
    session.add(CVSkill(cv_id=27, skill_id=1, proficiency_level="advanced"))
    session.add(JobSkill(job_id=1, skill_id=2, is_required=is_required))
    session.commit()
    # Mô phỏng hai hệ thống cũ cùng quy đổi C và C++ thành c.
    session.get(Skill, 2).normalized_name = "c"
    result = calculate_match_score(session.get(CV, 27), session.get(Job, 1), session)
    session.rollback()
    assert result["match_score"] == 0
    assert result["matched_skills"] == []


@pytest.mark.parametrize("is_required", [True, False])
def test_matching_recognizes_same_name_with_different_legacy_keys(skill_api, is_required):
    _, session = skill_api
    session.add_all([
        Skill(id=1, name="Node.Js", normalized_name="nodejs"),
        Skill(id=2, name="node.js", normalized_name="node.js"),
        Job(id=1, title="Backend", level="junior"),
    ])
    session.flush()
    session.add(CVSkill(cv_id=27, skill_id=1, proficiency_level="advanced"))
    session.add(JobSkill(job_id=1, skill_id=2, is_required=is_required))
    session.commit()
    result = calculate_match_score(session.get(CV, 27), session.get(Job, 1), session)
    assert result["match_score"] == 100


@pytest.mark.parametrize("name", [" ", "+++", "Python\x00", "ß" * 255])
@pytest.mark.parametrize("path,name_field", [("/api/skills/", "name"), ("/api/jobs/admin", "skill_name")])
def test_invalid_skill_names_are_rejected_before_writing(skill_api, name, path, name_field):
    client, session = skill_api
    payload = {"name": name} if name_field == "name" else {"title": "Test", "required_skills": [{"skill_name": name}]}
    response = client.post(path, json=payload)
    assert response.status_code == 422, response.text
    assert session.query(Skill).count() == 0
    assert session.query(Job).count() == 0


@pytest.mark.parametrize("manual_first", [True, False])
def test_matching_keeps_manual_level_when_legacy_alias_has_ai_level(skill_api, manual_first):
    _, session = skill_api
    session.add_all([
        Skill(id=1, name="Node.Js", normalized_name="nodejs"),
        Skill(id=2, name="node.js", normalized_name="node.js"),
        Job(id=1, title="Backend", level="junior"),
    ])
    session.flush()
    manual_skill_id = 1 if manual_first else 2
    ai_skill_id = 2 if manual_first else 1
    session.add_all([
        CVSkill(id=manual_skill_id, cv_id=27, skill_id=manual_skill_id, source="manual", proficiency_level="beginner"),
        CVSkill(id=ai_skill_id, cv_id=27, skill_id=ai_skill_id, source="ai_extracted", proficiency_level="advanced"),
        JobSkill(job_id=1, skill_id=1, is_required=True),
    ])
    session.commit()
    result = calculate_match_score(session.get(CV, 27), session.get(Job, 1), session)
    assert result["match_score"] == 0
    assert result["weak_skills"][0]["current_level"] == "beginner"
