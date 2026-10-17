"""Phối hợp tác vụ phân tích và DELETE bằng DB/file tạm, không gọi AI thật."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, local
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Query, sessionmaker

from app.api import cv as cv_api
from app.api.admin import router as admin_router
from app.core import database
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models import job, profile, skill_gap
from app.models.cv import CV
from app.models.skill import CVSkill, Skill
from app.models.user import User


RAW_TEXT = "Python developer, email actual@example.com, phone 0901234567"
ANALYSIS = {
    "summary": "A local test result",
    "skills": [{"name": "Docker", "category": "devops", "proficiency_level": "advanced", "years_experience": 2}],
}


@pytest.fixture
def analysis_api(tmp_path, monkeypatch):
    root = tmp_path / "cvs"
    root.mkdir()
    original = root / "owner.pdf"
    original.write_bytes(b"temporary analysis input")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(root))
    # Separate connections are needed for actual worker/API threads.
    engine = create_engine(f"sqlite:///{(tmp_path / 'analysis.sqlite').as_posix()}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    with sessions() as session:
        session.add_all([
            User(id=4, email="owner@example.com", full_name="Owner", password_hash="test"),
            User(id=1, email="admin@example.com", full_name="Admin", password_hash="test", role="admin"),
            Skill(id=65, name="Python", normalized_name="python"),
        ])
        session.flush()
        session.add(CV(id=27, user_id=4, filename="owner.pdf", file_path=str(original), status="uploaded", file_hash="analysis-delete-race"))
        session.flush()
        session.add(CVSkill(cv_id=27, skill_id=65, source="manual", proficiency_level="expert", years_experience=5))
        session.commit()

    background_sessions = []
    worker_context = local()

    def background_session():
        session = sessions()
        background_sessions.append(session)
        worker_context.session = session
        return session

    monkeypatch.setattr(database, "SessionLocal", background_session)
    parser_calls = []
    ai_calls = []

    def parse(path):
        assert not worker_context.session.in_transaction()
        parser_calls.append(path)
        return RAW_TEXT

    def analyze(raw_text, path):
        assert not worker_context.session.in_transaction()
        ai_calls.append((raw_text, path))
        return ANALYSIS

    monkeypatch.setattr(cv_api, "extract_text_from_file", parse)
    monkeypatch.setattr(cv_api, "analyze_cv_with_ai", analyze)
    actor = {"id": 4, "role": "user"}

    def test_db():
        with sessions() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app = FastAPI()
    app.include_router(cv_api.router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**actor)
    try:
        with TestClient(configure_http_errors(app, ["http://localhost:5173"])) as client:
            yield SimpleNamespace(
                client=client, sessions=sessions, actor=actor, original=original,
                parser_calls=parser_calls, ai_calls=ai_calls, background_sessions=background_sessions,
            )
    finally:
        engine.dispose()


def delete_cv(api, scope):
    api.actor.update(id=1 if scope == "admin" else 4, role="admin" if scope == "admin" else "user")
    path = "/api/admin/cvs/27" if scope == "admin" else "/api/cv/27"
    response = api.client.delete(path)
    assert response.status_code == 204, response.text


def assert_no_result_was_recreated(api):
    assert not api.original.exists()
    with api.sessions() as session:
        assert session.get(CV, 27) is None
        assert session.query(CVSkill).count() == 0
        assert [s.name for s in session.query(Skill).all()] == ["Python"]
    assert all(not session.in_transaction() for session in api.background_sessions)
    lock = cv_api._get_analysis_lock("analysis-delete-race")
    assert lock.acquire(blocking=False), "The canceled analysis left its hash lock held"
    lock.release()


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_task_started_after_deletion_skips_parser_and_ai(analysis_api, scope):
    api = analysis_api
    delete_cv(api, scope)
    cv_api.process_cv_analysis(27, str(api.original))
    assert api.parser_calls == []
    assert api.ai_calls == []
    assert_no_result_was_recreated(api)


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_deletion_while_task_waits_for_same_hash_analysis(analysis_api, monkeypatch, scope):
    api = analysis_api
    held_lock = cv_api._get_analysis_lock("analysis-delete-race")
    held_lock.acquire()
    waiting = Event()

    def report_waiting(_file_hash):
        assert not api.background_sessions[-1].in_transaction()
        waiting.set()
        return held_lock

    with monkeypatch.context() as scoped:
        scoped.setattr(cv_api, "_get_analysis_lock", report_waiting)
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(cv_api.process_cv_analysis, 27, str(api.original))
            try:
                assert waiting.wait(timeout=15)
                delete_cv(api, scope)
            finally:
                held_lock.release()
            task.result(timeout=15)
    assert api.parser_calls == []
    assert api.ai_calls == []
    assert_no_result_was_recreated(api)


@pytest.mark.parametrize("scope", ["owner", "admin"])
@pytest.mark.parametrize("stage", ["parser", "ai"])
@pytest.mark.parametrize("raises_error", [False, True])
def test_deletion_during_worker_io_drops_result_and_error(analysis_api, monkeypatch, scope, stage, raises_error):
    api = analysis_api
    reached = Event()
    resume = Event()

    def paused_io(*args):
        assert not api.background_sessions[-1].in_transaction()
        calls = api.parser_calls if stage == "parser" else api.ai_calls
        calls.append(args)
        reached.set()
        assert resume.wait(timeout=15), "The test did not release the worker"
        if raises_error:
            raise OSError("simulated failure after CV deletion")
        return RAW_TEXT if stage == "parser" else ANALYSIS

    target = "extract_text_from_file" if stage == "parser" else "analyze_cv_with_ai"
    monkeypatch.setattr(cv_api, target, paused_io)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(cv_api.process_cv_analysis, 27, str(api.original))
        try:
            assert reached.wait(timeout=15), "The worker did not reach the expected I/O stage"
            delete_cv(api, scope)
        finally:
            resume.set()
        task.result(timeout=15)
    if stage == "parser":
        assert api.ai_calls == []
    assert_no_result_was_recreated(api)


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_cached_result_does_not_write_after_target_is_deleted(analysis_api, monkeypatch, scope):
    api = analysis_api
    with api.sessions() as session:
        session.add(CV(
            id=28, user_id=4, filename="cached.pdf", file_path="cached.pdf", status="analyzed",
            file_hash="analysis-delete-race", raw_text=RAW_TEXT, ai_analysis=ANALYSIS,
        ))
        session.commit()
    reached = Event()
    resume = Event()
    real_lookup = cv_api._get_cv_for_analysis_update
    lookups = []

    def pause_before_cache_publication(session, cv_id):
        lookups.append(cv_id)
        if len(lookups) == 2:
            assert not session.in_transaction()
            reached.set()
            assert resume.wait(timeout=15)
        return real_lookup(session, cv_id)

    monkeypatch.setattr(cv_api, "_get_cv_for_analysis_update", pause_before_cache_publication)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(cv_api.process_cv_analysis, 27, str(api.original))
        try:
            assert reached.wait(timeout=15)
            delete_cv(api, scope)
        finally:
            resume.set()
        task.result(timeout=15)
    assert api.parser_calls == []
    assert api.ai_calls == []
    assert_no_result_was_recreated(api)
    with api.sessions() as session:
        assert session.get(CV, 28).status == "analyzed"
        assert session.get(CV, 28).ai_analysis == ANALYSIS


def test_successful_analysis_publishes_skills_and_preserves_manual_provenance(analysis_api):
    api = analysis_api
    # The worker uses the stored path, even if an old queued argument differs.
    cv_api.process_cv_analysis(27, "old-queued-path.pdf")
    assert api.parser_calls == [str(api.original)]
    assert api.ai_calls == [(RAW_TEXT, str(api.original))]
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.status == "analyzed"
        assert cv.raw_text == RAW_TEXT
        assert cv.ai_analysis == ANALYSIS
        manual = session.query(CVSkill).filter_by(cv_id=27, skill_id=65).one()
        assert manual.source == "manual"
        assert manual.proficiency_level == "expert"
        assert manual.years_experience == 5
        ai_link = session.query(CVSkill).filter(CVSkill.skill_id != 65).one()
        assert ai_link.source == "ai_extracted"
        assert ai_link.skill.name == "Docker"


@pytest.mark.parametrize("stage", ["parser", "ai"])
def test_existing_cv_is_marked_failed_on_analysis_exception(analysis_api, monkeypatch, stage):
    def fail(*_args):
        raise RuntimeError("isolated analysis failure")

    target = "extract_text_from_file" if stage == "parser" else "analyze_cv_with_ai"
    monkeypatch.setattr(cv_api, target, fail)
    cv_api.process_cv_analysis(27, str(analysis_api.original))
    with analysis_api.sessions() as session:
        assert session.get(CV, 27).status == "failed"
        assert session.query(Skill).count() == 1
        assert session.query(CVSkill).one().source == "manual"
    assert analysis_api.original.exists()


def test_legacy_cv_without_hash_drops_result_after_deletion(analysis_api, monkeypatch):
    api = analysis_api
    with api.sessions() as session:
        session.get(CV, 27).file_hash = None
        session.commit()

    def delete_during_ai(raw_text, path):
        assert not api.background_sessions[-1].in_transaction()
        assert raw_text == RAW_TEXT
        assert path == str(api.original)
        delete_cv(api, "owner")
        return ANALYSIS

    monkeypatch.setattr(cv_api, "analyze_cv_with_ai", delete_during_ai)
    cv_api.process_cv_analysis(27, str(api.original))
    assert_no_result_was_recreated(api)


def set_attempt(api, status="analyzed", run_id="a" * 32, age_minutes=0, file_hash=None):
    with api.sessions() as session:
        cv = session.get(CV, 27)
        cv.status = status
        cv.analysis_run_id = run_id
        cv.file_hash = file_hash
        cv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=age_minutes)
        session.commit()


@pytest.mark.parametrize("status", ["uploaded", "processing"])
def test_reanalyze_rejects_recent_pending_attempt_without_scheduling(analysis_api, monkeypatch, status):
    api = analysis_api
    set_attempt(api, status=status)
    tasks = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))
    response = api.client.post("/api/cv/27/reanalyze")
    assert response.status_code == 409
    assert tasks == []
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.status == status
        assert cv.analysis_run_id == "a" * 32
        assert session.query(CVSkill).one().source == "manual"


@pytest.mark.parametrize("status,age", [("analyzed", 0), ("failed", 0), ("uploaded", 31), ("processing", 31)])
def test_reanalyze_creates_new_attempt_before_scheduling(analysis_api, monkeypatch, status, age):
    api = analysis_api
    set_attempt(api, status=status, age_minutes=age)
    tasks = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))
    response = api.client.post("/api/cv/27/reanalyze")
    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"
    assert "analysis_run_id" not in response.json()
    assert len(tasks) == 1
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.status == "uploaded"
        assert len(cv.analysis_run_id) == 32
        assert cv.analysis_run_id != "a" * 32
        assert tasks[0] == (27, str(api.original), cv.analysis_run_id)
    assert api.client.post("/api/cv/27/reanalyze").status_code == 409
    assert len(tasks) == 1


def test_two_simultaneous_reanalyze_requests_schedule_one_attempt(analysis_api, monkeypatch):
    api = analysis_api
    set_attempt(api)
    tasks = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))
    barrier = Barrier(2, timeout=15)
    real_first = Query.first

    def read_before_other_request_updates(query):
        result = real_first(query)
        if result is not None and query.column_descriptions[0]["entity"] is CV:
            barrier.wait()
        return result

    with monkeypatch.context() as scoped:
        scoped.setattr(Query, "first", read_before_other_request_updates)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks_http = [pool.submit(api.client.post, "/api/cv/27/reanalyze") for _ in range(2)]
            responses = [task.result(timeout=20) for task in tasks_http]
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert len(tasks) == 1
    with api.sessions() as session:
        assert session.get(CV, 27).analysis_run_id == tasks[0][2]


@pytest.mark.parametrize("explicit_run_id", [False, True])
def test_two_workers_can_only_claim_one_queued_attempt(analysis_api, monkeypatch, explicit_run_id):
    api = analysis_api
    run_id = "a" * 32 if explicit_run_id else None
    set_attempt(api, status="uploaded", run_id=run_id)
    barrier = Barrier(2, timeout=15)
    per_thread = local()
    real_lookup = cv_api._get_cv_for_analysis_update

    def align_initial_claims(session, cv_id):
        if not getattr(per_thread, "entered", False):
            per_thread.entered = True
            barrier.wait()
        return real_lookup(session, cv_id)

    monkeypatch.setattr(cv_api, "_get_cv_for_analysis_update", align_initial_claims)
    with ThreadPoolExecutor(max_workers=2) as pool:
        workers = [pool.submit(cv_api.process_cv_analysis, 27, str(api.original), run_id) for _ in range(2)]
        for worker in workers:
            worker.result(timeout=20)
    assert len(api.parser_calls) == 1
    assert len(api.ai_calls) == 1
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.status == "analyzed"
        saved_run_id = cv.analysis_run_id
        assert len(saved_run_id) == 32
        assert session.query(CVSkill).count() == 2
    # A repeated delivery of the completed attempt must not call AI again.
    cv_api.process_cv_analysis(27, str(api.original), saved_run_id)
    assert len(api.ai_calls) == 1


@pytest.mark.parametrize("stage", ["parser", "ai"])
@pytest.mark.parametrize("raises_error", [False, True])
def test_obsolete_worker_cannot_overwrite_new_result_or_mark_it_failed(analysis_api, monkeypatch, stage, raises_error):
    api = analysis_api
    old_run_id = "a" * 32
    set_attempt(api, status="uploaded", run_id=old_run_id)
    reached = Event()
    resume = Event()
    real_worker = cv_api.process_cv_analysis
    original_parse = cv_api.extract_text_from_file
    tasks = []
    calls = []
    new_analysis = {"summary": "New attempt wins", "skills": [{"name": "Kubernetes", "category": "devops"}]}

    def parse(path):
        if stage == "parser" and not calls:
            calls.append("old-parser")
            reached.set()
            assert resume.wait(timeout=15)
            if raises_error:
                raise RuntimeError("late old parser error")
            return "Old extracted text"
        return original_parse(path)

    def analyze(_raw_text, _path):
        if stage == "ai" and not calls:
            calls.append("old-ai")
            reached.set()
            assert resume.wait(timeout=15)
            if raises_error:
                raise RuntimeError("late old AI error")
            return ANALYSIS
        return new_analysis

    monkeypatch.setattr(cv_api, "extract_text_from_file", parse)
    monkeypatch.setattr(cv_api, "analyze_cv_with_ai", analyze)
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))
    with ThreadPoolExecutor(max_workers=1) as pool:
        old_task = pool.submit(real_worker, 27, str(api.original), old_run_id)
        try:
            assert reached.wait(timeout=15)
            # Make this attempt eligible for the existing 30-minute recovery rule.
            with api.sessions() as session:
                session.get(CV, 27).updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=31)
                session.commit()
            assert api.client.post("/api/cv/27/reanalyze").status_code == 200
            assert len(tasks) == 1
            real_worker(*tasks[0])
            with api.sessions() as session:
                assert session.get(CV, 27).ai_analysis == new_analysis
        finally:
            resume.set()
        old_task.result(timeout=15)
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.analysis_run_id == tasks[0][2]
        assert cv.status == "analyzed"
        assert cv.ai_analysis == new_analysis
        assert cv.raw_text == RAW_TEXT
        assert sorted(s.name for s in session.query(Skill)) == ["Kubernetes", "Python"]
        assert session.query(CVSkill).filter_by(skill_id=65).one().source == "manual"


@pytest.mark.parametrize("run_id", [None, "b" * 32])
def test_unidentified_or_obsolete_delivery_cannot_claim_current_attempt(analysis_api, run_id):
    api = analysis_api
    set_attempt(api, status="uploaded")
    cv_api.process_cv_analysis(27, str(api.original), run_id)
    assert api.parser_calls == []
    assert api.ai_calls == []
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.analysis_run_id == "a" * 32
        assert cv.status == "uploaded"


def test_failed_reanalyze_commit_preserves_old_attempt_and_schedules_nothing(analysis_api, monkeypatch):
    api = analysis_api
    set_attempt(api)
    tasks = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))

    def fail_commit(session):
        session.flush()
        raise OperationalError("COMMIT", {}, RuntimeError("isolated retry failure"))

    event.listen(api.sessions, "before_commit", fail_commit)
    try:
        response = api.client.post("/api/cv/27/reanalyze")
    finally:
        event.remove(api.sessions, "before_commit", fail_commit)
    assert response.status_code == 503
    assert tasks == []
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.analysis_run_id == "a" * 32
        assert cv.status == "analyzed"


def test_obsolete_cached_attempt_cannot_complete_newly_queued_attempt(analysis_api, monkeypatch):
    api = analysis_api
    old_run_id = "a" * 32
    set_attempt(api, status="uploaded", file_hash="analysis-delete-race")
    with api.sessions() as session:
        session.add(CV(
            id=28, user_id=4, filename="cached.pdf", file_path="cached.pdf", status="analyzed",
            file_hash="analysis-delete-race", raw_text=RAW_TEXT, ai_analysis=ANALYSIS,
        ))
        session.commit()
    real_worker = cv_api.process_cv_analysis
    real_lookup = cv_api._get_cv_for_analysis_update
    reached = Event()
    resume = Event()
    lookups = []
    tasks = []

    def pause_cache_publish(session, cv_id):
        lookups.append(cv_id)
        if len(lookups) == 2:
            reached.set()
            assert resume.wait(timeout=15)
        return real_lookup(session, cv_id)

    monkeypatch.setattr(cv_api, "_get_cv_for_analysis_update", pause_cache_publish)
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda *args: tasks.append(args))
    with ThreadPoolExecutor(max_workers=1) as pool:
        old_task = pool.submit(real_worker, 27, str(api.original), old_run_id)
        try:
            assert reached.wait(timeout=15)
            with api.sessions() as session:
                session.get(CV, 27).updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=31)
                session.commit()
            assert api.client.post("/api/cv/27/reanalyze").status_code == 200
        finally:
            resume.set()
        old_task.result(timeout=15)
    assert len(tasks) == 1
    with api.sessions() as session:
        cv = session.get(CV, 27)
        assert cv.status == "uploaded"
        assert cv.analysis_run_id == tasks[0][2]
        assert cv.ai_analysis is None
        assert session.query(Skill).count() == 1
        assert session.query(CVSkill).one().source == "manual"
    real_worker(*tasks[0])
    with api.sessions() as session:
        assert session.get(CV, 27).status == "analyzed"
        assert session.get(CV, 27).analysis_run_id == tasks[0][2]
    assert api.ai_calls == []
