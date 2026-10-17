import pytest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.cv import _normalize_skill_name, _save_cv_skills, router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.core.http_errors import configure_http_errors
from app.models.cv import CV
from app.models.skill import CVSkill, Skill
from app.models.user import User
# Đăng ký đầy đủ các model có relationship trước khi tạo DB kiểm thử.
from app.models import job, profile, skill_gap
from app.schemas.cv import CVSkillManualRequest


def test_manual_skill_normalization_is_stable():
    assert _normalize_skill_name(" React.js ") == "react.js"
    assert _normalize_skill_name("Machine Learning") == "machine_learning"


def test_manual_skill_request_validates_provenance_fields():
    request = CVSkillManualRequest(
        skill_name="Python",
        proficiency_level="advanced",
        years_experience=3,
    )

    assert request.skill_name == "Python"
    assert request.proficiency_level == "advanced"
    assert request.years_experience == 3


def test_manual_skill_request_rejects_negative_experience():
    with pytest.raises(ValueError):
        CVSkillManualRequest(skill_name="Python", years_experience=-1)


@pytest.fixture
def manual_skill_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=4, email="test@example.com", password_hash="test", full_name="Test"))
    session.add(CV(id=27, user_id=4, filename="test.pdf", file_path="test.pdf", status="analyzed"))
    session.add(Skill(id=65, name="Node.Js", normalized_name="node.js", category="framework"))
    session.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4)
    wrapped_app = configure_http_errors(app, ["http://localhost:5173"])
    try:
        with TestClient(wrapped_app, raise_server_exceptions=False) as client:
            yield client, session, app
    finally:
        session.close()
        engine.dispose()


def test_manual_nodejs_reuses_existing_skill_and_updates_link(manual_skill_api):
    client, session, _ = manual_skill_api
    payload = {"skill_name": " Node.js ", "proficiency_level": "advanced", "years_experience": 2}
    response = client.post("/api/cv/27/skills", json=payload, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json()["skill_id"] == 65
    assert response.json()["source"] == "manual"
    assert session.query(Skill).count() == 1
    assert session.query(CVSkill).count() == 1
    payload["years_experience"] = 3
    updated = client.post("/api/cv/27/skills", json=payload)
    assert updated.status_code == 201
    assert updated.json()["years_experience"] == 3
    assert session.query(CVSkill).count() == 1
    assert session.get(Skill, 65).normalized_name == "node.js"


def test_manual_skill_cannot_modify_another_users_cv(manual_skill_api):
    client, session, app = manual_skill_api
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=99)
    response = client.post("/api/cv/27/skills", json={"skill_name": "Node.js"})
    assert response.status_code == 404
    assert session.query(CVSkill).count() == 0


@pytest.mark.parametrize("payload", [
    {"skill_name": ""},
    {"skill_name": "   "},
    {"skill_name": "+++"},
    {"skill_name": "Python\x00"},
    {"skill_name": "Python\u200b"},
    {"skill_name": "x" * 256},
    {"skill_name": "ß" * 255},
    {"skill_name": None},
    {"skill_name": ["Python"]},
    {"skill_name": "Python", "years_experience": -1},
    {"skill_name": "Python", "years_experience": 81},
    {"skill_name": "Python", "years_experience": "NaN"},
    {"skill_name": "Python", "years_experience": "Infinity"},
    {"skill_name": "Python", "years_experience": True},
    {"skill_name": "Python", "years_experience": "abc"},
    {"skill_name": "Python", "proficiency_level": "master"},
    {},
])
def test_invalid_manual_skill_requests_return_422_without_writes(manual_skill_api, payload):
    client, session, _ = manual_skill_api
    response = client.post("/api/cv/27/skills", json=payload, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 422
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert session.query(Skill).count() == 1
    assert session.query(CVSkill).count() == 0


def test_symbols_and_vietnamese_skill_names_are_distinct(manual_skill_api):
    client, session, _ = manual_skill_api
    for name in ["C", "C++", "C#", "Kỹ năng giao tiếp"]:
        response = client.post("/api/cv/27/skills", json={"skill_name": name, "years_experience": 0.5})
        assert response.status_code == 201
    assert session.query(CVSkill).count() == 4
    assert {s.normalized_name for s in session.query(Skill).all()} >= {"c", "c++", "c#", "kỹ_năng_giao_tiếp"}


def test_legacy_colliding_normalization_does_not_merge_c_and_cpp(manual_skill_api):
    client, session, _ = manual_skill_api
    session.add(Skill(name="C++", normalized_name="c", category="programming_language"))
    session.commit()
    assert client.post("/api/cv/27/skills", json={"skill_name": "C++"}).status_code == 201
    assert client.post("/api/cv/27/skills", json={"skill_name": "C#"}).status_code == 201
    response = client.post("/api/cv/27/skills", json={"skill_name": "C"})
    assert response.status_code == 409
    assert session.query(CVSkill).count() == 2


def test_deleted_skill_restored_and_existing_ai_link_becomes_manual(manual_skill_api):
    client, session, _ = manual_skill_api
    skill = session.get(Skill, 65)
    skill.is_deleted = True
    session.add(CVSkill(cv_id=27, skill_id=65, source="ai_extracted"))
    session.commit()
    response = client.post("/api/cv/27/skills", json={"skill_name": "node.js"})
    assert response.status_code == 201
    assert response.json()["source"] == "manual"
    assert not session.get(Skill, 65).is_deleted
    assert session.query(CVSkill).count() == 1


def test_reanalysis_preserves_manual_skills_and_replaces_old_ai_links(manual_skill_api):
    client, session, _ = manual_skill_api
    session.add_all([
        Skill(id=66, name="Legacy Skill", normalized_name="legacy_skill", category="other"),
        CVSkill(
            cv_id=27,
            skill_id=65,
            proficiency_level="advanced",
            years_experience=4,
            source="manual",
        ),
        CVSkill(
            cv_id=27,
            skill_id=66,
            proficiency_level="beginner",
            years_experience=1,
            source="ai_extracted",
        ),
    ])
    session.commit()

    _save_cv_skills(
        27,
        [
            {"name": "Node.js", "proficiency_level": "beginner", "years_experience": 0},
            {"name": "Python", "proficiency_level": "advanced", "years_experience": 2},
        ],
        session,
    )
    session.commit()

    links = session.query(CVSkill).filter(CVSkill.cv_id == 27).all()
    by_skill_id = {link.skill_id: link for link in links}
    assert by_skill_id[65].source == "manual"
    assert by_skill_id[65].proficiency_level == "advanced"
    assert by_skill_id[65].years_experience == 4
    assert 66 not in by_skill_id
    python_link = next(link for link in links if link.skill.name == "Python")
    assert python_link.source == "ai_extracted"
    assert len(links) == 2


@pytest.mark.parametrize("status", ["uploaded", "processing"])
def test_pending_cv_rejects_skill_edits(manual_skill_api, status):
    client, session, _ = manual_skill_api
    session.get(CV, 27).status = status
    session.commit()
    assert client.post("/api/cv/27/skills", json={"skill_name": "Node.js"}).status_code == 409
    assert client.delete("/api/cv/27/skills/65").status_code == 409
    assert session.query(CVSkill).count() == 0


def test_delete_only_removes_link_and_missing_link_returns_404(manual_skill_api):
    client, session, _ = manual_skill_api
    client.post("/api/cv/27/skills", json={"skill_name": "Node.js"})
    assert client.delete("/api/cv/27/skills/65").status_code == 204
    assert session.query(Skill).count() == 1
    assert session.query(CVSkill).count() == 0
    assert client.delete("/api/cv/27/skills/65").status_code == 404


@pytest.mark.parametrize("path", ["/api/cv/0/skills", "/api/cv/-1/skills", "/api/cv/not-an-id/skills"])
def test_invalid_cv_id_returns_422(manual_skill_api, path):
    client, _, _ = manual_skill_api
    assert client.post(path, json={"skill_name": "Node.js"}).status_code == 422


def test_database_failure_returns_json_503_with_cors(manual_skill_api, monkeypatch):
    client, session, _ = manual_skill_api

    def unavailable(*args, **kwargs):
        raise OperationalError("select", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr(session, "query", unavailable)
    for method in ["get", "post", "delete"]:
        path = "/api/cv/27/skills/65" if method == "delete" else "/api/cv/27/skills"
        response = client.request(method, path, json={"skill_name": "Node.js"} if method == "post" else None,
                                  headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 503
        assert isinstance(response.json()["detail"], str)
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "database unavailable" not in response.text


def test_unexpected_error_has_safe_json_and_cors(manual_skill_api, monkeypatch):
    client, session, _ = manual_skill_api

    def unexpected(*args, **kwargs):
        raise RuntimeError("internal diagnostic information")

    monkeypatch.setattr(session, "query", unexpected)
    response = client.post("/api/cv/27/skills", json={"skill_name": "Node.js"},
                           headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert isinstance(response.json()["detail"], str)
    assert "internal diagnostic" not in response.text


def test_missing_authentication_returns_error_with_cors(manual_skill_api):
    client, _, app = manual_skill_api
    del app.dependency_overrides[get_current_user]
    response = client.post("/api/cv/27/skills", json={"skill_name": "Node.js"},
                           headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_and_rejected_origin(manual_skill_api):
    client, _, _ = manual_skill_api
    allowed = client.options("/api/cv/27/skills", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.options("/api/cv/27/skills", headers={
        "Origin": "https://untrusted.example",
        "Access-Control-Request-Method": "POST",
    })
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_invalid_json_returns_422_with_cors(manual_skill_api):
    client, _, _ = manual_skill_api
    response = client.post("/api/cv/27/skills", content="{", headers={
        "Origin": "http://localhost:5173", "Content-Type": "application/json",
    })
    assert response.status_code == 422
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_new_skill_flush_conflict_rolls_back_without_partial_links(manual_skill_api, monkeypatch):
    client, session, _ = manual_skill_api

    def conflict(*args, **kwargs):
        raise IntegrityError("insert", {}, RuntimeError("duplicate"))

    with monkeypatch.context() as scoped:
        scoped.setattr(session, "flush", conflict)
        response = client.post("/api/cv/27/skills", json={"skill_name": "Docker"})
    assert response.status_code == 409
    assert session.query(Skill).count() == 1
    assert session.query(CVSkill).count() == 0


def test_delete_failure_preserves_link(manual_skill_api, monkeypatch):
    client, session, _ = manual_skill_api
    client.post("/api/cv/27/skills", json={"skill_name": "Node.js"})

    def conflict():
        raise IntegrityError("delete", {}, RuntimeError("conflict"))

    monkeypatch.setattr(session, "commit", conflict)
    response = client.delete("/api/cv/27/skills/65", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 409
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert session.query(CVSkill).count() == 1


def test_manual_skill_integrity_conflict_returns_409_with_cors(manual_skill_api, monkeypatch):
    client, session, _ = manual_skill_api

    def conflict():
        raise IntegrityError("insert", {}, RuntimeError("duplicate"))

    monkeypatch.setattr(session, "commit", conflict)
    response = client.post(
        "/api/cv/27/skills",
        json={"skill_name": "Node.js"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 409
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert session.query(CVSkill).count() == 0
