import io
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import cv as cv_api
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models.user import User
from app.models import cv, job, profile, skill, skill_gap
from app.services import cv_upload


@pytest.fixture
def valid_pdf():
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Sample CV: Python, SQL, FastAPI")
        return document.tobytes()


@pytest.fixture
def upload_api(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    owner = User(id=4, email="upload@example.com", full_name="Upload test", password_hash="test")
    session.add(owner)
    session.commit()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    tasks = []
    monkeypatch.setattr(cv_api, "process_cv_analysis", lambda cv_id, file_path, run_id: tasks.append((cv_id, file_path, run_id)))
    app = FastAPI()
    app.include_router(cv_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: owner
    # Bỏ rate limit trong DB test riêng; không thay đổi rate limit production.
    route = next(route for route in cv_api.router.routes if route.path == "/cv/upload")
    for dependency in route.dependant.dependencies:
        if getattr(dependency.call, "__name__", "") == "check_rate_limit":
            app.dependency_overrides[dependency.call] = lambda: None
    try:
        with TestClient(configure_http_errors(app, ["http://localhost:5173"]), raise_server_exceptions=False) as client:
            yield client, session, tasks, tmp_path
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("mime", ["application/pdf", "application/octet-stream", "application/x-pdf", ""])
def test_readable_pdf_upload_accepts_browser_mime_variations(upload_api, valid_pdf, mime):
    client, session, tasks, directory = upload_api
    response = client.post("/api/cv/upload", files={"file": ("CV.PDF", valid_pdf, mime)},
                           headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 201, response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json()["status"] == "uploaded"
    assert session.query(cv.CV).count() == 1
    assert len(tasks) == 1
    assert tasks[0][2] == session.query(cv.CV).one().analysis_run_id
    assert len(tasks[0][2]) == 32
    assert next(directory.iterdir()).read_bytes() == valid_pdf


def test_readable_pdf_with_leading_bytes_is_not_rejected(upload_api, valid_pdf):
    client, _, _, _ = upload_api
    response = client.post("/api/cv/upload", files={"file": ("cv.pdf", b"\xef\xbb\xbf\n" + valid_pdf, "application/pdf")})
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("filename,contents", [
    ("cv.pdf", b""),
    ("cv.pdf", b"this is not a PDF"),
    ("cv.pdf", b"%PDF-1.7\nnot a real PDF"),
    ("cv.doc", b"legacy word file"),
    ("cv.docx", b"PKfake zip"),
])
def test_invalid_upload_returns_detail_without_saving_files(upload_api, filename, contents):
    client, session, tasks, directory = upload_api
    response = client.post("/api/cv/upload", files={"file": (filename, contents, "application/octet-stream")})
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)
    assert session.query(cv.CV).count() == 0
    assert not tasks
    assert not list(directory.iterdir())


def test_password_protected_pdf_returns_specific_error(upload_api):
    client, _, _, _ = upload_api
    with fitz.open() as document:
        document.new_page()
        protected = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    response = client.post("/api/cv/upload", files={"file": ("cv.pdf", protected, "application/pdf")})
    assert response.status_code == 400
    assert "mật khẩu" in response.json()["detail"]


def test_oversized_pdf_returns_specific_error(upload_api, valid_pdf):
    client, _, _, _ = upload_api
    oversized = valid_pdf + b" " * (1024 * 1024)
    response = client.post("/api/cv/upload", files={"file": ("cv.pdf", oversized, "application/pdf")})
    assert response.status_code == 400
    assert "1MB" in response.json()["detail"]


def test_valid_docx_upload_still_works(upload_api):
    client, _, tasks, _ = upload_api
    document = Document()
    document.add_paragraph("Sample CV: Python and SQL")
    content = io.BytesIO()
    document.save(content)
    response = client.post("/api/cv/upload", files={"file": ("cv.docx", content.getvalue(), "application/octet-stream")})
    assert response.status_code == 201
    assert len(tasks) == 1


def send_pdf(client, contents):
    return client.post(
        "/api/cv/upload", files={"file": ("cv.pdf", contents, "application/pdf")},
        headers={"Origin": "http://localhost:5173"},
    )


@pytest.mark.parametrize("stage", ["flush", "commit"])
def test_database_failure_cleans_new_file_and_does_not_start_ai(upload_api, valid_pdf, stage):
    client, session, tasks, directory = upload_api
    observed = []

    def fail_before_flush(_session, *_args):
        files = list(directory.iterdir())
        assert len(files) == 1
        assert files[0].read_bytes() == valid_pdf
        observed.append(True)
        raise OperationalError("INSERT", {}, RuntimeError("isolated database failure"))

    def fail_before_commit(_session):
        assert session.query(cv.CV).count() == 1
        fail_before_flush(session)

    event_name = "before_flush" if stage == "flush" else "before_commit"
    callback = fail_before_flush if stage == "flush" else fail_before_commit
    event.listen(session, event_name, callback)
    try:
        response = send_pdf(client, valid_pdf)
    finally:
        event.remove(session, event_name, callback)
    assert observed == [True]
    assert response.status_code == 503, response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert session.query(cv.CV).count() == 0
    assert list(directory.iterdir()) == []
    assert tasks == []
    # Retrying after a definite rollback creates one valid CV and one task.
    assert send_pdf(client, valid_pdf).status_code == 201
    assert session.query(cv.CV).count() == 1
    assert len(tasks) == 1
    assert len(list(directory.iterdir())) == 1


@pytest.mark.parametrize("stage", ["directory", "open", "partial_write"])
def test_storage_failure_returns_503_without_record_or_task(upload_api, valid_pdf, monkeypatch, stage):
    client, session, tasks, directory = upload_api
    real_mkdir = Path.mkdir
    real_open = Path.open

    def denied_directory(path, *args, **kwargs):
        if path == directory:
            raise PermissionError("isolated directory failure")
        return real_mkdir(path, *args, **kwargs)

    def failed_open(path, mode="r", *args, **kwargs):
        if path.parent == directory and mode == "xb":
            if stage == "open":
                raise PermissionError("isolated open failure")

            @contextmanager
            def partial_writer():
                with real_open(path, mode, *args, **kwargs) as output:
                    class Writer:
                        def write(self, contents):
                            output.write(contents[:20])
                            output.flush()
                            raise OSError("isolated disk-full failure")
                    yield Writer()

            return partial_writer()
        return real_open(path, mode, *args, **kwargs)

    if stage == "directory":
        monkeypatch.setattr(Path, "mkdir", denied_directory)
    else:
        monkeypatch.setattr(Path, "open", failed_open)
    response = send_pdf(client, valid_pdf)
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)
    assert session.query(cv.CV).count() == 0
    assert tasks == []
    assert list(directory.iterdir()) == []


def test_filename_collision_never_truncates_or_deletes_an_existing_file(upload_api, valid_pdf, monkeypatch):
    client, session, tasks, directory = upload_api
    existing = directory / ("a" * 32 + ".pdf")
    existing.write_bytes(b"preserve existing CV")
    monkeypatch.setattr(cv_upload.uuid, "uuid4", lambda: SimpleNamespace(hex="a" * 32))
    response = send_pdf(client, valid_pdf)
    assert response.status_code == 503
    assert existing.read_bytes() == b"preserve existing CV"
    assert list(directory.iterdir()) == [existing]
    assert session.query(cv.CV).count() == 0
    assert tasks == []


def test_no_post_commit_refresh_is_required_for_successful_upload(upload_api, valid_pdf, monkeypatch):
    client, session, tasks, directory = upload_api

    def unavailable_refresh(*_args, **_kwargs):
        raise OperationalError("SELECT", {}, RuntimeError("post-commit connection unavailable"))

    monkeypatch.setattr(session, "refresh", unavailable_refresh)
    response = send_pdf(client, valid_pdf)
    assert response.status_code == 201, response.text
    assert response.json()["created_at"]
    assert response.json()["status"] == "uploaded"
    assert len(tasks) == 1
    assert session.query(cv.CV).one().id == tasks[0][0]
    assert len(list(directory.iterdir())) == 1


def test_error_reported_after_commit_keeps_file_and_queues_one_task(upload_api, valid_pdf):
    client, session, tasks, directory = upload_api

    def lost_acknowledgement(_session):
        raise OperationalError("COMMIT", {}, RuntimeError("isolated lost commit acknowledgement"))

    event.listen(session, "after_commit", lost_acknowledgement)
    try:
        response = send_pdf(client, valid_pdf)
    finally:
        event.remove(session, "after_commit", lost_acknowledgement)
    assert response.status_code == 201, response.text
    row = session.query(cv.CV).one()
    assert row.id == response.json()["id"]
    assert Path(row.file_path).read_bytes() == valid_pdf
    assert len(list(directory.iterdir())) == 1
    assert tasks == [(row.id, row.file_path, row.analysis_run_id)]


@pytest.mark.parametrize("actually_committed", [False, True])
def test_unverifiable_commit_preserves_file_and_does_not_start_ai(upload_api, valid_pdf, monkeypatch, caplog, actually_committed):
    client, session, tasks, directory = upload_api

    def failed_commit(_session):
        raise OperationalError("COMMIT", {}, RuntimeError("isolated unknown outcome"))

    def unavailable_verification(*_args):
        raise OperationalError("SELECT", {}, RuntimeError("isolated verification unavailable"))

    monkeypatch.setattr(cv_upload, "_stored_cv_id", unavailable_verification)
    event_name = "after_commit" if actually_committed else "before_commit"
    event.listen(session, event_name, failed_commit)
    try:
        response = send_pdf(client, valid_pdf)
    finally:
        event.remove(session, event_name, failed_commit)
    assert response.status_code == 503
    assert "tải lại danh sách" in response.json()["detail"]
    files = list(directory.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == valid_pdf
    assert str(files[0]) in caplog.text
    assert "preserve file" in caplog.text
    assert session.query(cv.CV).count() == int(actually_committed)
    assert tasks == []


def test_cleanup_failure_is_logged_without_creating_a_record_or_ai_task(upload_api, valid_pdf, monkeypatch, caplog):
    client, session, tasks, directory = upload_api

    def fail_flush(_session, *_args):
        raise OperationalError("INSERT", {}, RuntimeError("isolated insert failure"))

    def fail_cleanup(_path, *_args, **_kwargs):
        raise PermissionError("isolated cleanup failure")

    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    event.listen(session, "before_flush", fail_flush)
    try:
        response = send_pdf(client, valid_pdf)
    finally:
        event.remove(session, "before_flush", fail_flush)
    assert response.status_code == 503
    files = list(directory.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == valid_pdf
    assert "requires cleanup" in caplog.text
    assert str(files[0]) in caplog.text
    assert session.query(cv.CV).count() == 0
    assert tasks == []


def test_response_validation_failure_rolls_back_before_commit(upload_api, valid_pdf, monkeypatch):
    client, session, tasks, directory = upload_api

    def invalid_response(*_args, **_kwargs):
        raise ValueError("isolated response validation failure")

    monkeypatch.setattr(cv_upload.CVResponse, "model_validate", invalid_response)
    response = send_pdf(client, valid_pdf)
    assert response.status_code == 500
    assert isinstance(response.json()["detail"], str)
    assert session.query(cv.CV).count() == 0
    assert list(directory.iterdir()) == []
    assert tasks == []


def test_confirmed_file_is_preserved_even_if_analysis_attempt_already_changed(upload_api, valid_pdf):
    client, session, tasks, directory = upload_api

    def acknowledgement_lost_after_another_update(_session):
        with Session(bind=session.get_bind()) as another_request:
            row = another_request.query(cv.CV).one()
            row.analysis_run_id = "b" * 32
            row.status = "processing"
            another_request.commit()
        raise OperationalError("COMMIT", {}, RuntimeError("isolated lost acknowledgement"))

    event.listen(session, "after_commit", acknowledgement_lost_after_another_update)
    try:
        response = send_pdf(client, valid_pdf)
    finally:
        event.remove(session, "after_commit", acknowledgement_lost_after_another_update)
    assert response.status_code == 201, response.text
    row = session.query(cv.CV).one()
    assert row.analysis_run_id == "b" * 32
    assert Path(row.file_path).read_bytes() == valid_pdf
    assert len(list(directory.iterdir())) == 1
    assert len(tasks) == 1
    assert tasks[0][2] != row.analysis_run_id
