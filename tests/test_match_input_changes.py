"""Không lưu so khớp cũ khi CV/Job thay đổi trong lúc tạo lời khuyên."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event, local
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.api import jobs as jobs_api
from app.api import cv as cv_api
from app.api.admin import router as admin_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models import profile
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill
from app.models.skill_gap import SkillGap
from app.models.user import User


@pytest.fixture
def matching_api(tmp_path, monkeypatch):
    root = tmp_path / "cvs"
    root.mkdir()
    original = root / "test.pdf"
    original.write_bytes(b"isolated matching fixture")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(root))
    engine = create_engine(f"sqlite:///{(tmp_path / 'matching.sqlite').as_posix()}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    with sessions() as session:
        session.add_all([
            User(id=4, email="owner@example.com", full_name="Owner", password_hash="test"),
            User(id=9, email="other@example.com", full_name="Other", password_hash="test"),
            User(id=1, email="admin@example.com", full_name="Admin", password_hash="test", role="admin"),
            Skill(id=1, name="Python", normalized_name="python"),
            Skill(id=2, name="Docker", normalized_name="docker"),
            Skill(id=3, name="SQL", normalized_name="sql"),
            Job(id=7, title="Senior Backend", level="senior"),
        ])
        session.flush()
        session.add(CV(
            id=27, user_id=4, filename="test.pdf", file_path=str(original), status="analyzed",
            analysis_run_id="a" * 32, ai_analysis={"summary": "Python developer"},
        ))
        session.flush()
        session.add_all([
            CVSkill(id=11, cv_id=27, skill_id=1, proficiency_level="advanced", years_experience=2, source="manual"),
            JobSkill(id=21, job_id=7, skill_id=1, is_required=True, importance="high"),
            JobSkill(id=22, job_id=7, skill_id=2, is_required=False, importance="high"),
        ])
        session.commit()

    context = local()
    request_sessions = []

    def test_db():
        with sessions() as session:
            context.session = session
            request_sessions.append(session)
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    calls = []

    def recommendation(**kwargs):
        assert not context.session.in_transaction(), "The request kept a DB transaction open during AI I/O"
        calls.append(deepcopy(kwargs))
        return "New recommendation"

    monkeypatch.setattr(jobs_api, "generate_recommendation", recommendation)
    queued = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: queued.append(args))
    actor = {"id": 4, "role": "user"}
    app = FastAPI()
    app.include_router(jobs_api.router, prefix="/api")
    app.include_router(cv_api.router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**actor)
    for route in app.routes:
        for dependency in getattr(getattr(route, "dependant", None), "dependencies", []):
            if getattr(dependency.call, "__name__", "") == "check_rate_limit":
                app.dependency_overrides[dependency.call] = lambda: None
    try:
        with TestClient(configure_http_errors(app, ["http://localhost:5173"]), raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                client=client, sessions=sessions, actor=actor, calls=calls, context=context,
                queued=queued, original=original, request_sessions=request_sessions,
            )
    finally:
        engine.dispose()


def seed_existing_result(api):
    with api.sessions() as session:
        session.add(SkillGap(
            id=201, user_id=4, cv_id=27, job_id=7, match_score=12,
            matched_skills=[], missing_skills=[], weak_skills=[], ai_recommendation="Original recommendation",
        ))
        session.commit()


def run_match_while_changing(api, monkeypatch, change):
    reached = Event()
    resume = Event()

    def paused_recommendation(**_kwargs):
        assert not api.context.session.in_transaction()
        reached.set()
        assert resume.wait(timeout=15)
        return "Obsolete recommendation"

    monkeypatch.setattr(jobs_api, "generate_recommendation", paused_recommendation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(api.client.post, "/api/jobs/7/match/27", headers={"Origin": "http://localhost:5173"})
        try:
            assert reached.wait(timeout=15), "Matching did not reach the recommendation stage"
            change()
        finally:
            resume.set()
        return request.result(timeout=15)


def mutate_input(session, change):
    if change == "cv_level":
        session.get(CVSkill, 11).proficiency_level = "beginner"
    elif change == "cv_years":
        session.get(CVSkill, 11).years_experience = 7
    elif change == "cv_source":
        session.get(CVSkill, 11).source = "ai_extracted"
    elif change == "cv_add_skill":
        session.add(CVSkill(cv_id=27, skill_id=2, proficiency_level="expert", source="manual"))
    elif change == "cv_remove_skill":
        session.delete(session.get(CVSkill, 11))
    elif change == "cv_analysis":
        session.get(CV, 27).ai_analysis = {"summary": "A different CV summary"}
    elif change == "cv_new_run":
        session.get(CV, 27).analysis_run_id = "b" * 32
    elif change == "job_title":
        session.get(Job, 7).title = "Updated Position"
    elif change == "job_level":
        session.get(Job, 7).level = "intern"
    elif change == "job_company":
        session.get(Job, 7).company = "Updated Company"
    elif change == "job_importance":
        session.get(JobSkill, 21).importance = "low"
    elif change == "job_required":
        session.get(JobSkill, 22).is_required = True
    elif change == "job_add_skill":
        session.add(JobSkill(job_id=7, skill_id=3, is_required=True, importance="high"))
    elif change == "job_remove_skill":
        session.delete(session.get(JobSkill, 21))
    elif change == "skill_name":
        session.get(Skill, 1).name = "Python 3"
    else:
        raise AssertionError(f"Unknown test input change: {change}")


@pytest.mark.parametrize("change", [
    "cv_level", "cv_years", "cv_source", "cv_add_skill", "cv_remove_skill", "cv_analysis", "cv_new_run", "skill_name",
])
def test_history_detects_cv_input_changes_and_rematch_confirms_current_data(matching_api, change):
    api = matching_api
    first_response = api.client.post("/api/jobs/7/match/27")
    assert first_response.status_code == 200, first_response.text
    first = first_response.json()
    assert first["cv_match_status"] == "current"
    assert "cv_input_hash" not in first
    with api.sessions() as session:
        original_hash = session.get(SkillGap, first["id"]).cv_input_hash
        assert len(original_hash) == 64
        mutate_input(session, change)
        session.commit()
    history = api.client.get("/api/jobs/history/gaps")
    assert history.status_code == 200, history.text
    result = history.json()[0]
    assert result == {**first, "cv_match_status": "changed"}
    with api.sessions() as session:
        assert session.get(SkillGap, first["id"]).cv_input_hash == original_hash
    rematch = api.client.post("/api/jobs/7/match/27")
    assert rematch.status_code == 200, rematch.text
    assert rematch.json()["cv_match_status"] == "current"
    assert rematch.json()["id"] == first["id"]
    assert api.client.get("/api/jobs/history/gaps").json() == [rematch.json()]
    with api.sessions() as session:
        assert session.get(SkillGap, first["id"]).cv_input_hash != original_hash


@pytest.mark.parametrize("cv_status,expected", [("uploaded", "processing"), ("processing", "processing"), ("failed", "failed")])
def test_history_marks_pending_or_failed_cv_without_replacing_saved_result(matching_api, cv_status, expected):
    api = matching_api
    first = api.client.post("/api/jobs/7/match/27").json()
    with api.sessions() as session:
        cv = session.get(CV, 27)
        cv.analysis_run_id = "b" * 32
        cv.status = cv_status
        session.commit()
    history = api.client.get("/api/jobs/history/gaps")
    assert history.status_code == 200, history.text
    assert history.json() == [{**first, "cv_match_status": expected}]


@pytest.mark.parametrize("fingerprint", [None, "invalid"])
def test_legacy_or_invalid_cv_fingerprint_remains_unknown_without_backfill(matching_api, fingerprint):
    api = matching_api
    seed_existing_result(api)
    with api.sessions() as session:
        session.get(SkillGap, 201).cv_input_hash = fingerprint
        session.commit()
    response = api.client.get("/api/jobs/history/gaps")
    assert response.status_code == 200, response.text
    assert response.json()[0]["cv_match_status"] == "unknown"
    assert response.json()[0]["match_score"] == 12
    with api.sessions() as session:
        assert session.get(SkillGap, 201).cv_input_hash == fingerprint


def test_manual_skill_api_updates_history_status_but_not_the_saved_score(matching_api):
    api = matching_api
    first = api.client.post("/api/jobs/7/match/27").json()
    unchanged = api.client.post("/api/cv/27/skills", json={
        "skill_name": "Python", "proficiency_level": "advanced", "years_experience": 2,
    })
    assert unchanged.status_code == 201, unchanged.text
    assert api.client.get("/api/jobs/history/gaps").json() == [first]
    saved = api.client.post("/api/cv/27/skills", json={
        "skill_name": "Python", "proficiency_level": "beginner", "years_experience": 0,
    })
    assert saved.status_code == 201, saved.text
    assert saved.json()["source"] == "manual"
    assert api.client.get("/api/jobs/history/gaps").json() == [{**first, "cv_match_status": "changed"}]
    removed = api.client.delete("/api/cv/27/skills/1")
    assert removed.status_code == 204, removed.text
    assert api.client.get("/api/jobs/history/gaps").json() == [{**first, "cv_match_status": "changed"}]
    rematch = api.client.post("/api/jobs/7/match/27").json()
    assert rematch["cv_match_status"] == "current"
    assert rematch["match_score"] == 0


def test_reanalysis_api_marks_previous_result_until_a_new_match(matching_api):
    api = matching_api
    first = api.client.post("/api/jobs/7/match/27").json()
    queued = api.client.post("/api/cv/27/reanalyze")
    assert queued.status_code == 200, queued.text
    assert api.queued
    assert api.client.get("/api/jobs/history/gaps").json() == [{**first, "cv_match_status": "processing"}]
    with api.sessions() as session:
        session.get(CV, 27).status = "analyzed"
        session.commit()
    assert api.client.get("/api/jobs/history/gaps").json() == [{**first, "cv_match_status": "changed"}]
    rematch = api.client.post("/api/jobs/7/match/27").json()
    assert rematch["cv_match_status"] == "current"


def test_cv_fingerprint_ignores_json_key_order_and_unrelated_job_changes(matching_api):
    api = matching_api
    with api.sessions() as session:
        session.get(CV, 27).ai_analysis = {"summary": "Developer", "education": {"school": "School", "year": 2026}}
        session.commit()
    first = api.client.post("/api/jobs/7/match/27").json()
    with api.sessions() as session:
        session.get(CV, 27).ai_analysis = {"education": {"year": 2026, "school": "School"}, "summary": "Developer"}
        session.get(Job, 7).title = "Updated Position"
        session.add(CV(id=28, user_id=4, filename="other.pdf", file_path="other.pdf", status="analyzed"))
        session.flush()
        session.add(CVSkill(cv_id=28, skill_id=2, proficiency_level="expert", source="manual"))
        session.commit()
    response = api.client.get("/api/jobs/history/gaps")
    assert response.status_code == 200, response.text
    assert response.json() == [first]


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("change", [
    "cv_level", "cv_years", "cv_source", "cv_add_skill", "cv_remove_skill", "cv_analysis", "cv_new_run",
    "job_title", "job_level", "job_company", "job_importance", "job_required", "job_add_skill", "job_remove_skill", "skill_name",
])
def test_changed_input_rejects_old_result_without_overwriting_history(matching_api, monkeypatch, existing, change):
    api = matching_api
    if existing:
        seed_existing_result(api)

    def update():
        with api.sessions() as session:
            mutate_input(session, change)
            session.commit()

    response = run_match_while_changing(api, monkeypatch, update)
    assert response.status_code == 409, response.text
    assert "so khớp lại" in response.json()["detail"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    with api.sessions() as session:
        assert session.query(SkillGap).count() == int(existing)
        if existing:
            result = session.get(SkillGap, 201)
            assert result.match_score == 12
            assert result.ai_recommendation == "Original recommendation"


@pytest.mark.parametrize("path", ["/api/cv/27", "/api/admin/cvs/27"])
@pytest.mark.parametrize("existing", [False, True])
def test_cv_deleted_during_ai_does_not_recreate_history(matching_api, monkeypatch, path, existing):
    api = matching_api
    if existing:
        seed_existing_result(api)

    def delete():
        if path.startswith("/api/admin"):
            api.actor.update(id=1, role="admin")
        assert api.client.delete(path).status_code == 204

    response = run_match_while_changing(api, monkeypatch, delete)
    assert response.status_code == 404
    with api.sessions() as session:
        assert session.get(CV, 27) is None
        assert session.query(SkillGap).count() == 0
    assert not api.original.exists()


@pytest.mark.parametrize("change,status_code", [("job_inactive", 404), ("job_deleted", 404), ("cv_owner", 404), ("user_locked", 401)])
def test_unavailable_inputs_or_locked_account_stop_persistence(matching_api, monkeypatch, change, status_code):
    api = matching_api
    seed_existing_result(api)

    def update():
        with api.sessions() as session:
            if change == "job_inactive":
                session.get(Job, 7).is_active = False
            elif change == "job_deleted":
                session.get(Job, 7).is_deleted = True
            elif change == "cv_owner":
                session.get(CV, 27).user_id = 9
            else:
                session.get(User, 4).is_active = False
            session.commit()

    response = run_match_while_changing(api, monkeypatch, update)
    assert response.status_code == status_code
    if status_code == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    with api.sessions() as session:
        assert session.get(SkillGap, 201).match_score == 12
        assert session.get(SkillGap, 201).ai_recommendation == "Original recommendation"


def test_actual_reanalysis_request_during_matching_returns_retry_message(matching_api, monkeypatch):
    api = matching_api

    def reanalyze():
        response = api.client.post("/api/cv/27/reanalyze")
        assert response.status_code == 200
        assert len(api.queued) == 1

    response = run_match_while_changing(api, monkeypatch, reanalyze)
    assert response.status_code == 409
    with api.sessions() as session:
        assert session.get(CV, 27).status == "uploaded"
        assert session.query(SkillGap).count() == 0


def test_actual_job_edit_during_matching_is_detected(matching_api, monkeypatch):
    api = matching_api

    def edit_job():
        api.actor.update(id=1, role="admin")
        response = api.client.put("/api/jobs/admin/7", json={"required_skills": [{"skill_name": "SQL", "importance": "high"}]})
        assert response.status_code == 200, response.text

    response = run_match_while_changing(api, monkeypatch, edit_job)
    assert response.status_code == 409
    with api.sessions() as session:
        assert session.query(SkillGap).count() == 0
        assert [row.skill.name for row in session.query(JobSkill).filter_by(job_id=7, is_required=True)] == ["SQL"]


def test_unchanged_inputs_keep_formula_and_upsert_one_result(matching_api):
    api = matching_api
    first = api.client.post("/api/jobs/7/match/27")
    second = api.client.post("/api/jobs/7/match/27")
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["match_score"] == 66.7
    assert second.json()["skill_group_scores"][0]["score"] == 66.7
    assert len(api.calls) == 2
    assert api.calls[0]["job_title"] == "Senior Backend"
    assert api.calls[0]["missing_skills"][0]["skill_name"] == "Docker"
    with api.sessions() as session:
        assert session.query(SkillGap).count() == 1
        assert session.query(CVSkill).one().source == "manual"
        assert session.query(SkillGap).one().ai_recommendation == "New recommendation"


@pytest.mark.parametrize("cv_status", ["uploaded", "processing", "failed"])
def test_pending_cv_is_rejected_before_recommendation(matching_api, cv_status):
    api = matching_api
    with api.sessions() as session:
        session.get(CV, 27).status = cv_status
        session.commit()
    assert api.client.post("/api/jobs/7/match/27").status_code == 400
    assert api.calls == []


def test_integrity_failure_rolls_back_existing_result_without_unchecked_retry(matching_api):
    api = matching_api
    seed_existing_result(api)

    def fail_commit(_session):
        raise IntegrityError("UPDATE", {}, RuntimeError("isolated match conflict"))

    event.listen(api.sessions, "before_commit", fail_commit)
    try:
        response = api.client.post("/api/jobs/7/match/27")
    finally:
        event.remove(api.sessions, "before_commit", fail_commit)
    assert response.status_code == 409
    with api.sessions() as session:
        assert session.query(SkillGap).count() == 1
        assert session.get(SkillGap, 201).match_score == 12
        assert session.get(SkillGap, 201).ai_recommendation == "Original recommendation"


def test_recommendation_error_preserves_existing_result(matching_api, monkeypatch):
    api = matching_api
    seed_existing_result(api)

    def fail(**_kwargs):
        assert not api.context.session.in_transaction()
        raise RuntimeError("isolated recommendation error")

    monkeypatch.setattr(jobs_api, "generate_recommendation", fail)
    response = api.client.post("/api/jobs/7/match/27")
    assert response.status_code == 500
    with api.sessions() as session:
        assert session.get(SkillGap, 201).match_score == 12
        assert session.get(SkillGap, 201).ai_recommendation == "Original recommendation"
