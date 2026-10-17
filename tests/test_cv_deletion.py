"""Xóa CV qua API với file tạm và các lỗi giao dịch có thể tái hiện."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.api.cv import router as cv_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models import profile
from app.models.cv import CV
from app.models.job import Job
from app.models.skill import CVSkill, Skill
from app.models.skill_gap import SkillGap
from app.models.user import User


FILE_BYTES = b"isolated CV deletion fixture"


@pytest.fixture
def deletion_api(tmp_path, monkeypatch):
    upload_root = tmp_path / "cvs"
    upload_root.mkdir()
    original = upload_root / "owner.pdf"
    original.write_bytes(FILE_BYTES)
    other_file = upload_root / "other.pdf"
    other_file.write_bytes(b"other user's CV")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    with sessions() as session:
        session.add_all([
            User(id=4, email="owner@example.com", full_name="Owner", password_hash="test"),
            User(id=9, email="other@example.com", full_name="Other", password_hash="test"),
            User(id=1, email="admin@example.com", full_name="Admin", password_hash="test", role="admin"),
            Skill(id=65, name="Python", normalized_name="python"),
            Job(id=7, title="Developer"),
        ])
        session.flush()
        session.add_all([
            CV(id=27, user_id=4, filename="owner.pdf", file_path=str(original), status="analyzed"),
            CV(id=28, user_id=9, filename="other.pdf", file_path=str(other_file), status="analyzed"),
        ])
        session.flush()
        session.add_all([
            CVSkill(id=101, cv_id=27, skill_id=65, source="manual"),
            SkillGap(id=201, user_id=4, cv_id=27, job_id=7, match_score=80),
        ])
        session.commit()

    def test_db():
        with sessions() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    actor = {"id": 4, "role": "user"}
    app = FastAPI()
    app.include_router(cv_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**actor)
    try:
        with TestClient(configure_http_errors(app, ["http://localhost:5173"]), raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                client=client, app=app, actor=actor, sessions=sessions,
                upload_root=upload_root, original=original, other_file=other_file, tmp_path=tmp_path,
            )
    finally:
        engine.dispose()


def delete_request(api, scope, cv_id=27):
    api.actor.update(id=1 if scope == "admin" else 4, role="admin" if scope == "admin" else "user")
    path = f"/api/admin/cvs/{cv_id}" if scope == "admin" else f"/api/cv/{cv_id}"
    return api.client.delete(path, headers={"Origin": "http://localhost:5173"})


def db_snapshot(api):
    with api.sessions() as session:
        return (
            [(cv.id, cv.user_id, cv.file_path, cv.status) for cv in session.query(CV).order_by(CV.id)],
            [(link.id, link.cv_id, link.skill_id, link.source) for link in session.query(CVSkill).order_by(CVSkill.id)],
            [(gap.id, gap.cv_id, gap.match_score) for gap in session.query(SkillGap).order_by(SkillGap.id)],
        )


def assert_deleted(api):
    assert not api.original.exists()
    assert list(api.upload_root.glob("*.deleting")) == []
    assert api.other_file.read_bytes() == b"other user's CV"
    with api.sessions() as session:
        assert session.get(CV, 27) is None
        assert session.get(CV, 28) is not None
        assert session.query(CVSkill).count() == 0
        assert session.query(SkillGap).count() == 0
        assert session.get(Skill, 65) is not None
        assert session.get(Job, 7) is not None


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_deletion_removes_original_and_dependencies_but_keeps_shared_catalog(deletion_api, scope):
    api = deletion_api
    observed = []

    def verify_file_is_still_recoverable_before_commit(session):
        session.flush()
        staged = list(api.upload_root.glob("*.deleting"))
        assert not api.original.exists()
        assert len(staged) == 1
        assert staged[0].read_bytes() == FILE_BYTES
        assert session.connection().execute(select(CV.id).where(CV.id == 27)).scalar_one_or_none() is None
        observed.append(True)

    event.listen(api.sessions, "before_commit", verify_file_is_still_recoverable_before_commit)
    try:
        response = delete_request(api, scope)
    finally:
        event.remove(api.sessions, "before_commit", verify_file_is_still_recoverable_before_commit)
    assert response.status_code == 204
    assert response.content == b""
    assert observed == [True]
    assert_deleted(api)
    assert delete_request(api, scope).status_code == 404


@pytest.mark.parametrize("scope", ["owner", "admin"])
@pytest.mark.parametrize("failure_stage", ["flush", "commit"])
def test_database_failure_restores_file_and_all_related_rows(deletion_api, scope, failure_stage):
    api = deletion_api
    before = db_snapshot(api)
    observed = []

    def fail_before_flush(session, *_args):
        staged = list(api.upload_root.glob("*.deleting"))
        assert not api.original.exists()
        assert len(staged) == 1
        assert staged[0].read_bytes() == FILE_BYTES
        observed.append(True)
        raise OperationalError("DELETE", {}, RuntimeError("simulated database failure"))

    def fail_before_commit(session):
        session.flush()
        assert session.connection().execute(select(CV.id).where(CV.id == 27)).scalar_one_or_none() is None
        fail_before_flush(session)

    event_name = "before_flush" if failure_stage == "flush" else "before_commit"
    callback = fail_before_flush if failure_stage == "flush" else fail_before_commit
    event.listen(api.sessions, event_name, callback)
    try:
        response = delete_request(api, scope)
    finally:
        event.remove(api.sessions, event_name, callback)
    assert observed == [True]
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert api.original.read_bytes() == FILE_BYTES
    assert list(api.upload_root.glob("*.deleting")) == []
    assert db_snapshot(api) == before
    assert delete_request(api, scope).status_code == 204
    assert_deleted(api)


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_file_rename_failure_keeps_database_and_original_file(deletion_api, monkeypatch, scope):
    api = deletion_api
    before = db_snapshot(api)
    real_rename = Path.rename

    def locked_file(path, target):
        if path == api.original:
            raise PermissionError("file is open in another process")
        return real_rename(path, target)

    monkeypatch.setattr(Path, "rename", locked_file)
    response = delete_request(api, scope)
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)
    assert api.original.read_bytes() == FILE_BYTES
    assert list(api.upload_root.glob("*.deleting")) == []
    assert db_snapshot(api) == before


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_missing_original_file_does_not_prevent_record_deletion(deletion_api, scope):
    deletion_api.original.unlink()
    assert delete_request(deletion_api, scope).status_code == 204
    assert_deleted(deletion_api)


@pytest.mark.parametrize("scope", ["owner", "admin"])
@pytest.mark.parametrize("path_kind", ["outside", "traversal", "root", "directory"])
def test_invalid_storage_path_is_rejected_without_touching_files(deletion_api, scope, path_kind):
    api = deletion_api
    outside = api.tmp_path / "outside.pdf"
    outside.write_bytes(b"must not be touched")
    directory = api.upload_root / "folder.pdf"
    directory.mkdir()
    child = directory / "preserve.txt"
    child.write_bytes(b"preserve directory contents")
    paths = {
        "outside": str(outside),
        "traversal": str(api.upload_root / ".." / "outside.pdf"),
        "root": str(api.upload_root),
        "directory": str(directory),
    }
    with api.sessions() as session:
        session.get(CV, 27).file_path = paths[path_kind]
        session.commit()
    before = db_snapshot(api)
    response = delete_request(api, scope)
    assert response.status_code == 409
    assert api.original.read_bytes() == FILE_BYTES
    assert outside.read_bytes() == b"must not be touched"
    assert child.read_bytes() == b"preserve directory contents"
    assert db_snapshot(api) == before


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_final_cleanup_failure_is_logged_after_successful_database_deletion(deletion_api, monkeypatch, caplog, scope):
    api = deletion_api
    real_unlink = Path.unlink

    def fail_cleanup(path, *args, **kwargs):
        if path.suffix == ".deleting":
            raise PermissionError("simulated cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    response = delete_request(api, scope)
    assert response.status_code == 204
    assert not api.original.exists()
    staged = list(api.upload_root.glob("*.deleting"))
    assert len(staged) == 1
    assert staged[0].read_bytes() == FILE_BYTES
    assert "requires cleanup" in caplog.text
    assert str(staged[0]) in caplog.text
    with api.sessions() as session:
        assert session.get(CV, 27) is None
        assert session.query(CVSkill).count() == 0
        assert session.query(SkillGap).count() == 0
    assert api.client.get("/api/cv/27/file").status_code == 404


@pytest.mark.parametrize("scope", ["owner", "admin"])
def test_failed_restore_keeps_staged_file_and_logs_recovery_path(deletion_api, monkeypatch, caplog, scope):
    api = deletion_api
    before = db_snapshot(api)
    real_rename = Path.rename

    def fail_restore(path, target):
        if path.suffix == ".deleting":
            raise PermissionError("simulated restore failure")
        return real_rename(path, target)

    def fail_commit(_session):
        raise OperationalError("COMMIT", {}, RuntimeError("simulated database failure"))

    monkeypatch.setattr(Path, "rename", fail_restore)
    event.listen(api.sessions, "before_commit", fail_commit)
    try:
        response = delete_request(api, scope)
    finally:
        event.remove(api.sessions, "before_commit", fail_commit)
    assert response.status_code == 503
    assert "khôi phục" in response.json()["detail"]
    staged = list(api.upload_root.glob("*.deleting"))
    assert len(staged) == 1
    assert staged[0].read_bytes() == FILE_BYTES
    assert db_snapshot(api) == before
    assert "Could not restore staged file" in caplog.text
    assert str(staged[0]) in caplog.text


def test_owner_cannot_delete_someone_elses_cv_or_use_admin_endpoint(deletion_api):
    api = deletion_api
    before = db_snapshot(api)
    assert delete_request(api, "owner", cv_id=28).status_code == 404
    assert api.client.delete("/api/admin/cvs/27").status_code == 403
    assert api.original.read_bytes() == FILE_BYTES
    assert api.other_file.read_bytes() == b"other user's CV"
    assert db_snapshot(api) == before


@pytest.mark.parametrize("path", ["/api/cv/27", "/api/admin/cvs/27"])
def test_anonymous_request_cannot_delete_cv(deletion_api, path):
    api = deletion_api
    before = db_snapshot(api)
    del api.app.dependency_overrides[get_current_user]
    assert api.client.delete(path).status_code == 401
    assert api.original.read_bytes() == FILE_BYTES
    assert db_snapshot(api) == before
