"""Kiểm tra dữ liệu tài khoản/hồ sơ trước khi ghi vào DB."""
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.http_errors import configure_http_errors
from app.core.security import get_current_user
from app.models import cv, job, skill, skill_gap
from app.models.profile import Profile
from app.models.user import User


@pytest.fixture
def profile_api(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "isolated-user-profile-test-secret-at-least-32-characters")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        session.add_all([
            User(id=4, email="owner@example.com", password_hash="unchanged", full_name="Owner"),
            User(id=99, email="other@example.com", password_hash="unchanged", full_name="Other"),
        ])
        session.flush()
        session.add_all([
            Profile(user_id=4, phone="0901234567", location="Hà Nội", job_title="Developer", bio="Original bio", github_url="https://github.com/owner"),
            Profile(user_id=99, location="Other location", bio="Private bio"),
        ])
        session.commit()

    def test_db():
        with sessions() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    def current_owner(db=Depends(get_db)):
        return db.get(User, 4)

    app = FastAPI()
    app.include_router(users_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = current_owner
    for route in app.routes:
        for dependency in getattr(getattr(route, "dependant", None), "dependencies", []):
            if getattr(dependency.call, "__name__", "") == "check_rate_limit":
                app.dependency_overrides[dependency.call] = lambda: None
    try:
        with TestClient(configure_http_errors(app, ["http://localhost:5173"]), raise_server_exceptions=False) as client:
            yield SimpleNamespace(client=client, sessions=sessions, app=app)
    finally:
        engine.dispose()


def database_snapshot(api):
    with api.sessions() as session:
        users = [(u.id, u.full_name, u.role, u.email, u.password_hash, u.is_active) for u in session.query(User).order_by(User.id)]
        profiles = [
            (p.id, p.user_id, p.phone, p.location, p.job_title, p.bio, p.linkedin_url, p.github_url)
            for p in session.query(Profile).order_by(Profile.id)
        ]
        return users, profiles


@pytest.mark.parametrize("name", [None, "", "   ", "\u00a0", "x" * 256, "🙂" * 256, "Tên\x00ẩn", "Tên\u200bẩn", "Tên\nkhác", 123, []])
@pytest.mark.parametrize("operation", ["update", "register", "account"])
def test_invalid_full_name_returns_422_without_writes(profile_api, operation, name):
    before = database_snapshot(profile_api)
    if operation == "register":
        response = profile_api.client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "Example-password-123", "full_name": name},
        )
    elif operation == "account":
        response = profile_api.client.put("/api/users/me/account", json={"full_name": name, "location": "Must not be saved"})
    else:
        response = profile_api.client.put("/api/users/me", json={"full_name": name})
    assert response.status_code == 422, response.text
    assert any(error["loc"][-1] == "full_name" for error in response.json()["detail"])
    assert database_snapshot(profile_api) == before


def test_name_is_trimmed_and_unicode_is_preserved(profile_api):
    response = profile_api.client.put("/api/users/me", json={"full_name": "  Nguyễn Thị Ánh  "})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Nguyễn Thị Ánh"
    assert "password_hash" not in response.json()
    with profile_api.sessions() as session:
        assert session.get(User, 4).full_name == "Nguyễn Thị Ánh"
        assert session.get(User, 99).full_name == "Other"


@pytest.mark.parametrize("name", ["A", "Á" * 255, "🙂" * 255])
def test_name_length_boundary_is_accepted(profile_api, name):
    response = profile_api.client.put("/api/users/me", json={"full_name": name})
    assert response.status_code == 200
    assert response.json()["full_name"] == name


def test_omitted_full_name_keeps_existing_value(profile_api):
    before = database_snapshot(profile_api)
    assert profile_api.client.put("/api/users/me", json={}).status_code == 200
    assert database_snapshot(profile_api) == before


@pytest.mark.parametrize("path", ["/api/users/me/profile", "/api/users/me/account"])
@pytest.mark.parametrize("field,value", [
    ("location", "x" * 256), ("job_title", "x" * 256), ("bio", "x" * 2001),
    ("location", "Hà\nNội"), ("job_title", "Dev\u200bOps"), ("bio", "Text\x00hidden"),
    ("phone", "1" * 21), ("phone", "123456"), ("phone", "1" * 16),
    ("phone", "+++++++"), ("phone", "(---)---"), ("phone", "090123abc7"),
    ("phone", "090+1234567"), ("phone", "٠٩٠١٢٣٤٥٦٧"), ("phone", "090\n1234567"),
    ("github_url", "https://"), ("linkedin_url", "https:///linkedin.com/person"),
    ("github_url", "javascript:alert(1)"), ("linkedin_url", "ftp://example.com/profile"),
    ("github_url", "https://user:password@example.com/profile"), ("github_url", "https://@example.com"),
    ("linkedin_url", "https://example.com/white space"), ("github_url", "https://example.com\\path"),
    ("github_url", "https://example.com:99999/profile"), ("linkedin_url", "https://[invalid"),
    ("github_url", "https://example.com/" + "x" * 500),
    ("linkedin_url", "https://example.com/" + "x" * 500),
    ("location", 123), ("github_url", []),
])
def test_invalid_profile_field_rejects_whole_request_before_writing(profile_api, path, field, value):
    before = database_snapshot(profile_api)
    payload = {"bio": "Must not be saved", "location": "Must not be saved", field: value}
    if path.endswith("/account"):
        payload["full_name"] = "Must not be saved"
    response = profile_api.client.put(path, json=payload)
    assert response.status_code == 422, response.text
    assert any(error["loc"][-1] == field for error in response.json()["detail"])
    assert database_snapshot(profile_api) == before


def test_valid_profile_update_trims_fields_and_preserves_unsent_fields(profile_api):
    response = profile_api.client.put("/api/users/me/profile", json={
        "phone": " +84 (90) 123-4567 ", "location": "  Đà Nẵng  ",
        "bio": " Dòng 1\nDòng 2\tghi chú ", "linkedin_url": " https://www.linkedin.com/in/example?lang=vi#intro ",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+84 (90) 123-4567"
    assert data["location"] == "Đà Nẵng"
    assert data["bio"] == "Dòng 1\nDòng 2\tghi chú"
    assert data["linkedin_url"] == "https://www.linkedin.com/in/example?lang=vi#intro"
    assert data["job_title"] == "Developer"
    assert data["github_url"] == "https://github.com/owner"
    with profile_api.sessions() as session:
        other = session.query(Profile).filter_by(user_id=99).one()
        assert other.location == "Other location"
        assert other.bio == "Private bio"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_explicit_empty_profile_values_clear_only_supplied_fields(profile_api, value):
    response = profile_api.client.put("/api/users/me/profile", json={"location": value, "github_url": value})
    assert response.status_code == 200
    assert response.json()["location"] is None
    assert response.json()["github_url"] is None
    assert response.json()["phone"] == "0901234567"
    assert response.json()["bio"] == "Original bio"


def test_profile_limits_match_database_and_ui(profile_api):
    url = "https://example.com/" + "x" * (500 - len("https://example.com/"))
    payload = {"phone": "+123456789012345", "location": "Á" * 255, "job_title": "🙂" * 255, "bio": "Á" * 2000, "linkedin_url": url, "github_url": url}
    response = profile_api.client.put("/api/users/me/profile", json=payload)
    assert response.status_code == 200
    for field, value in payload.items():
        assert response.json()[field] == value


@pytest.mark.parametrize("path,payload", [
    ("/api/users/me", {"full_name": "Change", "role": "admin"}),
    ("/api/users/me", {"full_name": "Change", "email": "new@example.com"}),
    ("/api/users/me/profile", {"location": "Change", "user_id": 99}),
    ("/api/users/me/profile", {"location": "Change", "avatar_url": "https://example.com/image"}),
])
def test_update_rejects_fields_outside_contract_without_writing(profile_api, path, payload):
    before = database_snapshot(profile_api)
    assert profile_api.client.put(path, json=payload).status_code == 422
    assert database_snapshot(profile_api) == before


def test_invalid_request_does_not_create_missing_profile(profile_api):
    with profile_api.sessions() as session:
        session.delete(session.query(Profile).filter_by(user_id=4).one())
        session.commit()
    before = database_snapshot(profile_api)
    assert profile_api.client.put("/api/users/me/profile", json={"github_url": "https://"}).status_code == 422
    assert database_snapshot(profile_api) == before
    response = profile_api.client.put("/api/users/me/profile", json={"location": "  Huế  "})
    assert response.status_code == 200
    assert response.json()["location"] == "Huế"
    assert response.json()["user_id"] == 4


@pytest.mark.parametrize("missing_profile", [False, True])
def test_account_read_returns_server_name_without_creating_profile(profile_api, missing_profile):
    if missing_profile:
        with profile_api.sessions() as session:
            session.delete(session.query(Profile).filter_by(user_id=4).one())
            session.commit()
    before = database_snapshot(profile_api)
    response = profile_api.client.get("/api/users/me/account")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == 4
    assert data["user"]["full_name"] == "Owner"
    assert "password_hash" not in data["user"]
    if missing_profile:
        assert data["profile"] is None
    else:
        assert data["profile"]["user_id"] == 4
        assert data["profile"]["location"] == "Hà Nội"
    assert database_snapshot(profile_api) == before


@pytest.mark.parametrize("missing_profile", [False, True])
def test_account_save_updates_name_and_profile_together(profile_api, missing_profile):
    if missing_profile:
        with profile_api.sessions() as session:
            session.delete(session.query(Profile).filter_by(user_id=4).one())
            session.commit()
    response = profile_api.client.put("/api/users/me/account", json={
        "full_name": "  Nguyễn Thị Ánh  ", "location": "  Đà Nẵng  ", "github_url": "", "bio": "Thông tin mới",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["full_name"] == "Nguyễn Thị Ánh"
    assert "password_hash" not in data["user"]
    assert data["profile"]["location"] == "Đà Nẵng"
    assert data["profile"]["github_url"] is None
    with profile_api.sessions() as session:
        assert session.get(User, 4).full_name == "Nguyễn Thị Ánh"
        profile = session.query(Profile).filter_by(user_id=4).one()
        assert profile.id == data["profile"]["id"]
        assert profile.location == "Đà Nẵng"
        assert profile.bio == "Thông tin mới"
        assert profile.phone == (None if missing_profile else "0901234567")
        assert session.get(User, 99).full_name == "Other"
        assert session.query(Profile).filter_by(user_id=99).one().bio == "Private bio"


def test_account_patch_preserves_unsent_name_and_profile_fields(profile_api):
    response = profile_api.client.put("/api/users/me/account", json={"location": None})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["full_name"] == "Owner"
    assert data["profile"]["location"] is None
    assert data["profile"]["bio"] == "Original bio"
    assert data["profile"]["phone"] == "0901234567"
    before = database_snapshot(profile_api)
    assert profile_api.client.put("/api/users/me/account", json={}).status_code == 200
    assert database_snapshot(profile_api) == before


@pytest.mark.parametrize("field,value", [("role", "admin"), ("email", "new@example.com"), ("user_id", 99), ("avatar_url", "https://example.com/image")])
def test_account_rejects_fields_outside_contract_before_writing(profile_api, field, value):
    before = database_snapshot(profile_api)
    response = profile_api.client.put("/api/users/me/account", json={"full_name": "Change", "location": "Change", field: value})
    assert response.status_code == 422
    assert database_snapshot(profile_api) == before


@pytest.mark.parametrize("missing_profile", [False, True])
def test_failed_account_commit_rolls_back_both_database_writes(profile_api, missing_profile):
    if missing_profile:
        with profile_api.sessions() as session:
            session.delete(session.query(Profile).filter_by(user_id=4).one())
            session.commit()
    before = database_snapshot(profile_api)
    observed = []

    def fail_commit_after_writes(session):
        # Verify both real SQL writes took place before simulating commit failure.
        session.flush()
        connection = session.connection()
        observed.append((
            connection.execute(select(User.full_name).where(User.id == 4)).scalar_one(),
            connection.execute(select(Profile.location).where(Profile.user_id == 4)).scalar_one(),
        ))
        raise OperationalError("COMMIT", {}, RuntimeError("simulated commit failure"))

    event.listen(profile_api.sessions, "before_commit", fail_commit_after_writes)
    try:
        response = profile_api.client.put(
            "/api/users/me/account", json={"full_name": "Pending name", "location": "Pending location"},
            headers={"Origin": "http://localhost:5173"},
        )
    finally:
        event.remove(profile_api.sessions, "before_commit", fail_commit_after_writes)
    assert observed == [("Pending name", "Pending location")]
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert isinstance(response.json()["detail"], str)
    assert database_snapshot(profile_api) == before
    # A new request can save successfully after the failed transaction was rolled back.
    assert profile_api.client.put("/api/users/me/account", json={"full_name": "Recovered name", "location": "Recovered location"}).status_code == 200


@pytest.mark.parametrize("path,payload", [
    ("/api/users/me/account", {"full_name": "Must not be saved", "location": "Must not be saved"}),
    ("/api/users/me/password", {"old_password": "unchanged", "new_password": "Must-not-be-saved-123"}),
])
def test_password_and_account_recheck_active_status_after_authentication(profile_api, path, payload):
    # This fixture overrides authentication, letting the handler's later guard run.
    with profile_api.sessions() as session:
        session.get(User, 4).is_active = False
        session.commit()
    before = database_snapshot(profile_api)
    response = profile_api.client.put(path, json=payload)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert isinstance(response.json()["detail"], str)
    assert database_snapshot(profile_api) == before
