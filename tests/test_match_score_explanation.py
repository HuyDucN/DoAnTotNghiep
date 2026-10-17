"""Điểm tổng và dữ liệu biểu đồ phải dùng cùng trọng số và quy tắc đạt."""
from types import SimpleNamespace
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.jobs import router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import profile
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.services import job_matching


@pytest.fixture
def match_api(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        User(id=4, email="owner@example.test", full_name="Owner", password_hash="test"),
        CV(id=27, user_id=4, filename="cv.pdf", file_path="cv.pdf", status="analyzed"),
        Job(id=1, title="Senior Backend", level="senior"),
        Skill(id=1, name="Python", normalized_name="python"),
        Skill(id=2, name="Docker", normalized_name="docker"),
    ])
    session.flush()
    session.add_all([
        JobSkill(job_id=1, skill_id=1, is_required=True, importance="high"),
        JobSkill(job_id=1, skill_id=2, is_required=False, importance="high"),
    ])
    session.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4)
    for route in app.routes:
        for dependency in getattr(getattr(route, "dependant", None), "dependencies", []):
            if getattr(dependency.call, "__name__", "") == "check_rate_limit":
                app.dependency_overrides[dependency.call] = lambda: None
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("python_level,with_docker,expected_score,matched_weight", [
    ("intermediate", True, 33.3, 0.5),
    ("advanced", False, 66.7, 1.0),
])
def test_api_chart_uses_same_weighted_percentage_as_total(match_api, python_level, with_docker, expected_score, matched_weight):
    client, session = match_api
    session.add(CVSkill(cv_id=27, skill_id=1, proficiency_level=python_level))
    if with_docker:
        session.add(CVSkill(cv_id=27, skill_id=2, proficiency_level="beginner"))
    session.commit()
    response = client.post("/api/jobs/1/match/27")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["match_score"] == expected_score
    high = next(group for group in result["skill_group_scores"] if group["importance"] == "high")
    assert high == {
        "importance": "high", "matched_weight": matched_weight,
        "total_weight": 1.5, "score": expected_score,
    }
    if with_docker:
        assert result["weak_skills"][0]["skill_name"] == "Python"
    # Lịch sử dùng các nhóm skill đã lưu, không dùng yêu cầu Job vừa thay đổi.
    session.query(JobSkill).filter(JobSkill.job_id == 1).update({"importance": "low"})
    session.commit()
    history = client.get("/api/jobs/history/gaps")
    assert history.status_code == 200, history.text
    assert history.json()[0]["skill_group_scores"] == result["skill_group_scores"]
    assert history.json()[0]["match_score"] == expected_score
    assert history.json()[0]["job"] == result["job"]


def test_empty_requirements_have_zero_total_and_zero_groups(match_api):
    client, session = match_api
    session.query(JobSkill).delete()
    session.commit()
    result = client.post("/api/jobs/1/match/27").json()
    assert result["match_score"] == 0
    assert len(result["skill_group_scores"]) == 3
    assert all(group["total_weight"] == 0 and group["score"] == 0 for group in result["skill_group_scores"])


def test_legacy_history_without_weight_metadata_does_not_invent_chart_values(match_api):
    client, session = match_api
    session.add(SkillGap(
        user_id=4, cv_id=27, job_id=1, match_score=73,
        matched_skills=[{"skill_id": 1, "skill_name": "Python"}],
        missing_skills=[], weak_skills=[],
    ))
    session.commit()
    response = client.get("/api/jobs/history/gaps")
    assert response.status_code == 200, response.text
    assert response.json()[0]["match_score"] == 73
    assert response.json()[0]["skill_group_scores"] is None
    assert response.json()[0]["job_snapshot_available"] is False
    assert response.json()[0]["matched_at"] is None
    assert response.json()[0]["cv_id"] == 27
    assert response.json()[0]["cv_filename"] == "cv.pdf"
    assert response.json()[0]["cv_match_status"] == "unknown"


def test_weak_and_missing_skills_add_no_earned_weight():
    from app.services.skill_matcher import summarize_skill_groups

    groups = summarize_skill_groups(
        [],
        [{"is_required": False, "importance": "low"}],
        [{"is_required": True, "importance": "high"}],
    )
    high = next(group for group in groups if group["importance"] == "high")
    low = next(group for group in groups if group["importance"] == "low")
    assert high == {"importance": "high", "matched_weight": 0, "total_weight": 1.0, "score": 0}
    assert low == {"importance": "low", "matched_weight": 0, "total_weight": 0.2, "score": 0}


def test_group_uses_same_medium_fallback_for_unknown_importance():
    from app.services.skill_matcher import summarize_skill_groups

    groups = summarize_skill_groups([{"is_required": True, "importance": None}], [], [])
    medium = next(group for group in groups if group["importance"] == "medium")
    assert medium == {"importance": "medium", "matched_weight": 0.8, "total_weight": 0.8, "score": 100}


@pytest.mark.parametrize("change", ["job_metadata", "job_closed", "job_deleted", "skill_name"])
def test_history_preserves_job_at_match_time_after_current_job_changes(match_api, change):
    client, session = match_api
    response = client.post("/api/jobs/1/match/27")
    assert response.status_code == 200
    matched = response.json()
    assert matched["job_snapshot_available"] is True
    assert datetime.fromisoformat(matched["matched_at"]).utcoffset() == timedelta(0)
    job = session.get(Job, 1)
    if change == "job_metadata":
        job.title = "Changed Role"
        job.company = "Changed Company"
        job.level = "intern"
        job.description = "Changed requirements"
        job.salary_min = 1234
        session.query(JobSkill).filter_by(job_id=1).update({"importance": "low"})
    elif change == "job_closed":
        job.is_active = False
    elif change == "job_deleted":
        job.is_deleted = True
        job.is_active = False
    else:
        session.get(Skill, 1).name = "Python 3"
    session.commit()
    history = client.get("/api/jobs/history/gaps")
    assert history.status_code == 200
    result = history.json()[0]
    assert result["job"] == matched["job"]
    assert result["match_score"] == matched["match_score"]
    assert result["matched_at"] == matched["matched_at"]
    assert result["job_snapshot_available"] is True


def test_rematch_updates_snapshot_and_match_time_without_changing_creation_time(match_api, monkeypatch):
    client, session = match_api
    clock = {"value": datetime(2026, 10, 16, 10, 0, 0, 123456, tzinfo=timezone.utc)}

    class Clock:
        @staticmethod
        def now(_timezone):
            return clock["value"]

    monkeypatch.setattr(job_matching, "datetime", Clock)
    first = client.post("/api/jobs/1/match/27").json()
    assert datetime.fromisoformat(first["matched_at"]).microsecond == 123456
    session.get(Job, 1).title = "New Title"
    session.get(Job, 1).company = "New Company"
    session.commit()
    clock["value"] += timedelta(days=1)
    response = client.post("/api/jobs/1/match/27")
    assert response.status_code == 200
    second = response.json()
    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]
    assert datetime.fromisoformat(second["matched_at"]) == clock["value"]
    assert second["job"]["title"] == "New Title"
    assert second["job"]["company"] == "New Company"
    history = client.get("/api/jobs/history/gaps").json()
    assert history == [second]
    assert session.query(SkillGap).count() == 1
    assert first["job"]["title"] == "Senior Backend"


def test_history_orders_results_by_last_match_time(match_api, monkeypatch):
    client, session = match_api
    session.add(Job(id=2, title="Second Position"))
    session.commit()
    clock = {"value": datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)}

    class Clock:
        @staticmethod
        def now(_timezone):
            return clock["value"]

    monkeypatch.setattr(job_matching, "datetime", Clock)
    first = client.post("/api/jobs/1/match/27").json()
    clock["value"] += timedelta(seconds=1)
    second = client.post("/api/jobs/2/match/27").json()
    clock["value"] += timedelta(seconds=1)
    refreshed = client.post("/api/jobs/1/match/27").json()
    history = client.get("/api/jobs/history/gaps").json()
    assert [result["id"] for result in history] == [first["id"], second["id"]]
    assert history[0]["matched_at"] == refreshed["matched_at"]
    assert session.query(SkillGap).count() == 2


def test_legacy_history_marks_unknown_job_and_time_without_backfill_or_db_writes(match_api):
    client, session = match_api
    original_rec = "Báº¡n"
    created = datetime(2020, 1, 2, 3, 4, 5)
    session.add(SkillGap(
        user_id=4, cv_id=27, job_id=1, match_score=73,
        matched_skills=[], missing_skills=[], weak_skills=[],
        ai_recommendation=original_rec, created_at=created,
    ))
    session.get(Job, 1).title = "Current Title"
    session.commit()
    response = client.get("/api/jobs/history/gaps")
    assert response.status_code == 200
    result = response.json()[0]
    assert result["job_snapshot_available"] is False
    assert result["matched_at"] is None
    assert result["job"]["title"] == "Current Title"
    assert result["ai_recommendation"] == "Bạn"
    assert not session.dirty
    session.expire_all()
    row = session.query(SkillGap).one()
    assert row.created_at == created
    assert row.ai_recommendation == original_rec
    assert row.job_snapshot is None
    assert row.matched_at is None


@pytest.mark.parametrize("bad_snapshot", ["empty", "text", "wrong_id"])
def test_invalid_job_snapshot_is_identified_without_modifying_stored_data(match_api, bad_snapshot):
    client, session = match_api
    first = client.post("/api/jobs/1/match/27").json()
    row = session.get(SkillGap, first["id"])
    bad_value = {} if bad_snapshot == "empty" else "invalid snapshot"
    if bad_snapshot == "wrong_id":
        bad_value = deepcopy(row.job_snapshot)
        bad_value["id"] = 999
    row.job_snapshot = bad_value
    session.get(Job, 1).title = "Current Title"
    session.commit()
    response = client.get("/api/jobs/history/gaps")
    assert response.status_code == 200
    result = response.json()[0]
    assert result["job_snapshot_available"] is False
    assert result["job"]["id"] == 1
    assert result["job"]["title"] == "Current Title"
    assert result["match_score"] == first["match_score"]
    assert not session.dirty
    assert session.get(SkillGap, first["id"]).job_snapshot == bad_value


def test_failed_rematch_rolls_back_snapshot_time_and_score_together(match_api):
    client, session = match_api
    first = client.post("/api/jobs/1/match/27").json()
    row = session.get(SkillGap, first["id"])
    old_snapshot = deepcopy(row.job_snapshot)
    old_matched_at = row.matched_at
    old_cv_hash = row.cv_input_hash
    session.get(Job, 1).title = "New Title"
    session.add(CVSkill(cv_id=27, skill_id=2, proficiency_level="advanced", source="manual"))
    session.commit()

    def conflict(_session):
        raise IntegrityError("UPDATE", {}, RuntimeError("isolated match failure"))

    event.listen(session, "before_commit", conflict)
    try:
        response = client.post("/api/jobs/1/match/27")
    finally:
        event.remove(session, "before_commit", conflict)
    assert response.status_code == 409
    row = session.get(SkillGap, first["id"])
    assert row.job_snapshot == old_snapshot
    assert row.matched_at == old_matched_at
    assert row.cv_input_hash == old_cv_hash
    assert row.match_score == first["match_score"]
    result = client.get("/api/jobs/history/gaps").json()[0]
    assert result["job"] == first["job"]
    assert result["cv_match_status"] == "changed"


@pytest.mark.parametrize("filename", ["cv.pdf", "Hồ sơ Nguyễn Văn An - Backend.pdf"])
def test_match_and_history_identify_the_linked_cv(match_api, filename):
    client, session = match_api
    session.get(CV, 27).filename = filename
    session.commit()
    response = client.post("/api/jobs/1/match/27")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["cv_id"] == 27
    assert result["cv_filename"] == filename
    history = client.get("/api/jobs/history/gaps")
    assert history.status_code == 200, history.text
    assert history.json() == [result]


def test_same_filename_cvs_keep_separate_results_when_one_is_rematched(match_api):
    client, session = match_api
    session.add(CV(id=28, user_id=4, filename="cv.pdf", file_path="second.pdf", status="analyzed"))
    session.flush()
    session.add(CVSkill(cv_id=28, skill_id=1, proficiency_level="advanced", source="manual"))
    session.commit()
    first_response = client.post("/api/jobs/1/match/27")
    second_response = client.post("/api/jobs/1/match/28")
    assert first_response.status_code == second_response.status_code == 200
    first, second = first_response.json(), second_response.json()
    assert first["cv_filename"] == second["cv_filename"] == "cv.pdf"
    assert first["id"] != second["id"]
    assert (first["cv_id"], first["match_score"]) == (27, 0)
    assert (second["cv_id"], second["match_score"]) == (28, 66.7)

    session.add(CVSkill(cv_id=27, skill_id=2, proficiency_level="advanced", source="manual"))
    session.commit()
    rematch = client.post("/api/jobs/1/match/27")
    assert rematch.status_code == 200, rematch.text
    refreshed = rematch.json()
    assert refreshed["id"] == first["id"]
    assert refreshed["match_score"] == 33.3
    history = client.get("/api/jobs/history/gaps").json()
    by_cv = {result["cv_id"]: result for result in history}
    assert len(history) == session.query(SkillGap).count() == 2
    assert by_cv == {27: refreshed, 28: second}


def test_cv_identity_in_history_does_not_expose_another_users_cv(match_api):
    client, session = match_api
    own = client.post("/api/jobs/1/match/27").json()
    session.add(User(id=9, email="other@example.test", full_name="Other", password_hash="test"))
    session.flush()
    session.add(CV(id=88, user_id=9, filename="private-other-user.pdf", file_path="private.pdf", status="analyzed"))
    session.flush()
    session.add(SkillGap(
        user_id=9, cv_id=88, job_id=1, match_score=99,
        matched_skills=[], missing_skills=[], weak_skills=[],
    ))
    session.commit()
    history = client.get("/api/jobs/history/gaps")
    assert history.status_code == 200, history.text
    assert history.json() == [own]
    denied = client.post("/api/jobs/1/match/88")
    assert denied.status_code == 404
    assert "private-other-user.pdf" not in history.text + denied.text


def test_history_loads_cv_identity_without_a_separate_query_for_each_report(match_api):
    client, session = match_api
    for cv_id in (28, 29):
        session.add(CV(id=cv_id, user_id=4, filename="cv.pdf", file_path=f"{cv_id}.pdf", status="analyzed"))
    session.flush()
    for cv_id in (27, 28, 29):
        session.add(CVSkill(cv_id=cv_id, skill_id=1, proficiency_level="advanced", source="manual"))
    session.commit()
    for cv_id in (27, 28, 29):
        response = client.post(f"/api/jobs/1/match/{cv_id}")
        assert response.status_code == 200, response.text
    session.expunge_all()
    selects = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        history = client.get("/api/jobs/history/gaps")
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert history.status_code == 200, history.text
    assert {result["cv_id"] for result in history.json()} == {27, 28, 29}
    assert all(result["cv_match_status"] == "current" for result in history.json())
    assert len(selects) == 1
