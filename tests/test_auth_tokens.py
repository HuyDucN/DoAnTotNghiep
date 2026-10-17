from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import (
    create_access_token,
    create_user_access_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import cv, job, profile, skill, skill_gap
from app.models.user import User


OLD_PASSWORD = "Original-password-123"
NEW_PASSWORD = "Replacement-password-456"
USER_ID = 4
EMAIL = "recovery@example.com"


@pytest.fixture(scope="module")
def original_hash():
    return hash_password(OLD_PASSWORD)


@pytest.fixture
def auth_api(monkeypatch, original_hash):
    monkeypatch.setattr(settings, "SECRET_KEY", "isolated-auth-test-secret-key-at-least-32-characters")
    monkeypatch.setattr(settings, "ALLOW_DEV_RESET_TOKEN", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        session.add(User(id=USER_ID, email=EMAIL, password_hash=original_hash, full_name="Recovery Test"))
        session.commit()

    def test_db():
        with sessions() as session:
            yield session

    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    # Rate limiting has its own tests; token cases must not share an IP budget.
    for route in app.routes:
        for dependency in getattr(getattr(route, "dependant", None), "dependencies", []):
            if getattr(dependency.call, "__name__", "") == "check_rate_limit":
                app.dependency_overrides[dependency.call] = lambda: None

    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, sessions=sessions, original_hash=original_hash, app=app)
    finally:
        engine.dispose()


def signed_claims(purpose="access", password_hash=None, **changes):
    binding = {}
    if password_hash is not None:
        token = (
            create_password_reset_token(USER_ID, password_hash)
            if purpose == "reset" else create_user_access_token(USER_ID, password_hash)
        )
        binding = decode_token(token)
    claims = {
        **binding,
        "sub": str(USER_ID),
        "purpose": purpose,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        **changes,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def request_reset_token(api):
    response = api.client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    return response.json()["devResetToken"]


def reset_password(api, token, password=NEW_PASSWORD):
    return api.client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def request_access_token(api, password=OLD_PASSWORD, email=EMAIL):
    response = api.client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def stored_hash(api):
    with api.sessions() as session:
        return session.get(User, USER_ID).password_hash


def test_login_returns_access_token_accepted_by_protected_route(auth_api):
    response = auth_api.client.post("/api/auth/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    claims = decode_token(token)
    assert claims["purpose"] == "access"
    assert claims["sub"] == str(USER_ID)
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == USER_ID
    assert "password_hash" not in response.json()


INVALID_SUBJECTS = [
    None, "", "abc", 4, False, ["4"], {}, "0", "-1", "1.5", " 4 ", "٤", "2147483648", "9" * 5000,
]


@pytest.mark.parametrize("subject", INVALID_SUBJECTS)
@pytest.mark.parametrize("purpose", ["access", "reset"])
def test_malformed_subject_is_rejected_without_writing_or_server_error(auth_api, subject, purpose):
    token = signed_claims(purpose, password_hash=auth_api.original_hash, sub=subject)
    if purpose == "access":
        response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    else:
        response = reset_password(auth_api, token)
        assert response.status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("claim", ["exp", "iat", "nbf"])
@pytest.mark.parametrize("value", [None, [], {}, "tomorrow", "9999999999", True, float("inf")])
def test_invalid_time_claim_is_rejected_without_server_error(auth_api, claim, value):
    token = signed_claims(password_hash=auth_api.original_hash, **{claim: value})
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("missing", ["sub", "exp", "purpose"])
@pytest.mark.parametrize("purpose", ["access", "reset"])
def test_required_claim_cannot_be_omitted(auth_api, missing, purpose):
    claims = decode_token(signed_claims(purpose, password_hash=auth_api.original_hash))
    del claims[missing]
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    if purpose == "access":
        response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    else:
        response = reset_password(auth_api, token)
        assert response.status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("invalid_kind", ["expired", "signature", "unparseable"])
@pytest.mark.parametrize("purpose", ["access", "reset"])
def test_invalid_token_is_rejected(auth_api, purpose, invalid_kind):
    if invalid_kind == "expired":
        token = signed_claims(
            purpose, password_hash=auth_api.original_hash,
            exp=int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
        )
    elif invalid_kind == "signature":
        claims = decode_token(signed_claims(purpose, password_hash=auth_api.original_hash))
        token = jwt.encode(claims, "another-isolated-test-key", algorithm=settings.ALGORITHM)
    else:
        token = "this-is-not-a-jwt"
    if purpose == "access":
        response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    else:
        response = reset_password(auth_api, token)
        assert response.status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


def test_access_and_reset_tokens_cannot_be_interchanged(auth_api):
    reset_token = request_reset_token(auth_api)
    access_token = request_access_token(auth_api)
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {reset_token}"})
    assert response.status_code == 401
    assert reset_password(auth_api, access_token).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("password", [NEW_PASSWORD, OLD_PASSWORD])
def test_successful_reset_invalidates_all_previously_issued_recovery_tokens(auth_api, password):
    token = request_reset_token(auth_api)
    claims = decode_token(token)
    now = int(datetime.now(timezone.utc).timestamp())
    assert 14 * 60 <= claims["exp"] - now <= 15 * 60
    assert auth_api.original_hash not in str(claims)
    assert OLD_PASSWORD not in str(claims)
    # A separately signed link for the same password version also expires on reset.
    claims["exp"] -= 1
    second_token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert second_token != token
    assert reset_password(auth_api, token, password).status_code == 200
    updated_hash = stored_hash(auth_api)
    assert updated_hash != auth_api.original_hash
    assert verify_password(password, updated_hash)
    assert reset_password(auth_api, token).status_code == 400
    assert reset_password(auth_api, second_token).status_code == 400
    assert stored_hash(auth_api) == updated_hash
    # Recovery continues to work after requesting a fresh link.
    assert reset_password(auth_api, request_reset_token(auth_api)).status_code == 200


def test_login_accepts_new_password_and_rejects_old_password_after_reset(auth_api):
    assert reset_password(auth_api, request_reset_token(auth_api)).status_code == 200
    old_login = auth_api.client.post("/api/auth/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    new_login = auth_api.client.post("/api/auth/login", json={"email": EMAIL, "password": NEW_PASSWORD})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_normal_password_change_invalidates_pending_recovery_token(auth_api):
    token = request_reset_token(auth_api)
    access_token = request_access_token(auth_api)
    response = auth_api.client.put(
        "/api/users/me/password",
        json={"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert reset_password(auth_api, token).status_code == 400
    assert verify_password(NEW_PASSWORD, stored_hash(auth_api))


def test_wrong_old_password_preserves_password_and_recovery_link(auth_api):
    token = request_reset_token(auth_api)
    access_token = request_access_token(auth_api)
    response = auth_api.client.put(
        "/api/users/me/password",
        json={"old_password": "incorrect-password", "new_password": NEW_PASSWORD},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash
    assert reset_password(auth_api, token).status_code == 200


@pytest.mark.parametrize("operation", ["reset", "change"])
def test_password_write_reloads_credentials_instead_of_using_cached_user(auth_api, operation):
    token = request_reset_token(auth_api)
    access_token = request_access_token(auth_api)
    with auth_api.sessions() as stale_session:
        cached_user = stale_session.get(User, USER_ID)
        # Simulate an already completed password update from another request.
        with auth_api.sessions() as writer:
            user = writer.get(User, USER_ID)
            user.password_hash = hash_password(NEW_PASSWORD)
            current_hash = user.password_hash
            writer.commit()
        assert cached_user.password_hash == auth_api.original_hash

        def stale_db():
            yield stale_session

        auth_api.app.dependency_overrides[get_db] = stale_db
        try:
            if operation == "reset":
                response = reset_password(auth_api, token, "Unexpected-password-789")
            else:
                response = auth_api.client.put(
                    "/api/users/me/password",
                    json={"old_password": OLD_PASSWORD, "new_password": "Unexpected-password-789"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            assert response.status_code == (400 if operation == "reset" else 401)
            assert cached_user.password_hash == current_hash
        finally:
            stale_session.rollback()
    assert stored_hash(auth_api) == current_hash


@pytest.mark.parametrize("version", [None, 123, [], {}, "x" * 64, "đ" * 64])
def test_missing_or_incorrect_password_binding_is_rejected(auth_api, version):
    token = signed_claims("reset", password_version=version)
    assert reset_password(auth_api, token).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


def test_legacy_reset_token_without_password_binding_is_rejected(auth_api):
    assert reset_password(auth_api, signed_claims("reset")).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


def test_recovery_token_is_bound_to_its_user(auth_api):
    token = create_password_reset_token(99, auth_api.original_hash)
    claims = decode_token(token)
    claims["sub"] = str(USER_ID)
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert reset_password(auth_api, token).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


def test_inactive_and_missing_accounts_get_same_recovery_response(auth_api):
    token = request_reset_token(auth_api)
    with auth_api.sessions() as session:
        session.get(User, USER_ID).is_active = False
        session.commit()
    inactive = auth_api.client.post("/api/auth/forgot-password", json={"email": EMAIL})
    missing = auth_api.client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})
    assert inactive.status_code == missing.status_code == 200
    assert inactive.json() == missing.json()
    assert "devResetToken" not in inactive.json()
    assert reset_password(auth_api, token).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("environment", ["production", "prod", "PRODUCTION"])
def test_production_never_exposes_recovery_token(auth_api, monkeypatch, environment):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    existing = auth_api.client.post("/api/auth/forgot-password", json={"email": EMAIL})
    missing = auth_api.client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})
    assert existing.status_code == missing.status_code == 200
    assert existing.json() == missing.json()
    assert "devResetToken" not in existing.json()


def test_development_token_requires_explicit_opt_in(auth_api, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_DEV_RESET_TOKEN", False)
    response = auth_api.client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    assert "devResetToken" not in response.json()


def test_registration_issues_bound_access_token(auth_api):
    response = auth_api.client.post(
        "/api/auth/register",
        json={"email": "new-user@example.com", "password": OLD_PASSWORD, "full_name": "New User"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    claims = decode_token(token)
    user_id = response.json()["user"]["id"]
    with auth_api.sessions() as session:
        password_hash = session.get(User, user_id).password_hash
    assert password_hash not in str(claims)
    assert OLD_PASSWORD not in str(claims)
    me = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["id"] == user_id


@pytest.mark.parametrize("operation", ["reset", "change"])
@pytest.mark.parametrize("password", [NEW_PASSWORD, OLD_PASSWORD])
@pytest.mark.parametrize("role", ["user", "admin", "employer"])
def test_password_update_revokes_existing_access_tokens(auth_api, operation, password, role):
    with auth_api.sessions() as session:
        session.get(User, USER_ID).role = role
        session.commit()
    first_token = request_access_token(auth_api)
    claims = decode_token(request_access_token(auth_api))
    claims["exp"] = decode_token(first_token)["exp"] - 1
    second_token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert first_token != second_token
    for token in (first_token, second_token):
        assert auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    if operation == "reset":
        response = reset_password(auth_api, request_reset_token(auth_api), password)
        assert response.json()["user_id"] == USER_ID
    else:
        response = auth_api.client.put(
            "/api/users/me/password",
            json={"old_password": OLD_PASSWORD, "new_password": password},
            headers={"Authorization": f"Bearer {first_token}"},
        )
    assert response.status_code == 200
    for token in (first_token, second_token):
        headers = {"Authorization": f"Bearer {token}"}
        me = auth_api.client.get("/api/users/me", headers=headers)
        assert me.status_code == 401
        assert me.headers["www-authenticate"] == "Bearer"
        assert auth_api.client.put("/api/users/me", json={"full_name": "Forbidden change"}, headers=headers).status_code == 401
    fresh_token = request_access_token(auth_api, password)
    me = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {fresh_token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Recovery Test"


def test_password_update_does_not_revoke_other_accounts(auth_api):
    with auth_api.sessions() as session:
        session.add(User(id=99, email="other@example.com", password_hash=auth_api.original_hash, full_name="Other User"))
        session.commit()
    other_token = request_access_token(auth_api, email="other@example.com")
    assert reset_password(auth_api, request_reset_token(auth_api)).status_code == 200
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 200
    assert response.json()["id"] == 99


def test_failed_password_change_keeps_current_access_token_valid(auth_api):
    token = request_access_token(auth_api)
    headers = {"Authorization": f"Bearer {token}"}
    response = auth_api.client.put(
        "/api/users/me/password",
        json={"old_password": "incorrect-password", "new_password": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 400
    assert auth_api.client.get("/api/users/me", headers=headers).status_code == 200
    assert stored_hash(auth_api) == auth_api.original_hash


def test_legacy_access_token_without_password_binding_is_rejected(auth_api):
    token = create_access_token({"sub": str(USER_ID)})
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("version", [None, 123, [], {}, "x" * 64, "đ" * 64])
def test_invalid_access_password_binding_is_rejected(auth_api, version):
    token = signed_claims(password_hash=auth_api.original_hash, password_version=version)
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_access_password_binding_is_scoped_to_user(auth_api):
    claims = decode_token(create_user_access_token(99, auth_api.original_hash))
    claims["sub"] = str(USER_ID)
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("purpose", ["access", "reset"])
def test_changing_purpose_cannot_reuse_password_binding(auth_api, purpose):
    original_purpose = "reset" if purpose == "access" else "access"
    claims = decode_token(signed_claims(original_purpose, password_hash=auth_api.original_hash))
    claims["purpose"] = purpose
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    if purpose == "access":
        response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    else:
        assert reset_password(auth_api, token).status_code == 400
    assert stored_hash(auth_api) == auth_api.original_hash


@pytest.mark.parametrize("role", ["user", "admin", "employer"])
def test_account_endpoints_require_authenticated_active_user(auth_api, role):
    with auth_api.sessions() as session:
        session.get(User, USER_ID).role = role
        session.commit()
    assert auth_api.client.get("/api/users/me/account").status_code == 401
    assert auth_api.client.put("/api/users/me/account", json={"full_name": "Not allowed"}).status_code == 401
    token = request_access_token(auth_api)
    headers = {"Authorization": f"Bearer {token}"}
    response = auth_api.client.get("/api/users/me/account", headers=headers)
    assert response.status_code == 200
    assert response.json()["user"]["id"] == USER_ID
    assert response.json()["user"]["full_name"] == "Recovery Test"
    assert response.json()["profile"] is None
    saved = auth_api.client.put(
        "/api/users/me/account", json={"full_name": "Updated Name", "location": "Huế"}, headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["profile"]["user_id"] == USER_ID
    assert saved.json()["user"]["role"] == role
    with auth_api.sessions() as session:
        session.get(User, USER_ID).is_active = False
        session.commit()
    assert auth_api.client.get("/api/users/me/account", headers=headers).status_code == 401
    assert auth_api.client.put("/api/users/me/account", json={"full_name": "Not allowed"}, headers=headers).status_code == 401
    with auth_api.sessions() as session:
        assert session.get(User, USER_ID).full_name == "Updated Name"


@pytest.mark.parametrize("path", ["/api/admin/users/4/active", "/api/users/admin/4/active"])
@pytest.mark.parametrize("role", ["user", "admin", "employer"])
def test_admin_lock_ends_access_for_existing_tokens_on_all_user_routes(auth_api, path, role):
    with auth_api.sessions() as session:
        session.get(User, USER_ID).role = role
        session.add(User(
            id=99, email="operator@example.com", password_hash=auth_api.original_hash,
            full_name="Operator", role="admin", is_active=True,
        ))
        session.commit()
    token = request_access_token(auth_api)
    headers = {"Authorization": f"Bearer {token}"}
    operator_token = request_access_token(auth_api, email="operator@example.com")
    operator_headers = {"Authorization": f"Bearer {operator_token}"}
    assert auth_api.client.put(
        "/api/users/me/account", json={"full_name": "Recovery Test", "location": "Original location"}, headers=headers,
    ).status_code == 200
    locked = auth_api.client.patch(path, json={"is_active": False}, headers=operator_headers)
    assert locked.status_code == 200
    assert locked.json()["is_active"] is False
    assert "password_hash" not in locked.json()

    for method, url, payload in [
        ("GET", "/api/users/me", None),
        ("GET", "/api/users/me/profile", None),
        ("GET", "/api/users/me/account", None),
        ("GET", "/api/admin/users", None),
        ("GET", "/api/users/admin", None),
        ("PUT", "/api/users/me", {"full_name": "Must not be saved"}),
        ("PUT", "/api/users/me/profile", {"location": "Must not be saved"}),
        ("PUT", "/api/users/me/account", {"full_name": "Must not be saved", "location": "Must not be saved"}),
        ("PUT", "/api/users/me/password", {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD}),
        ("PATCH", "/api/admin/users/99/active", {"is_active": False}),
        ("PATCH", "/api/users/admin/99/active", {"is_active": False}),
    ]:
        response = auth_api.client.request(method, url, json=payload, headers=headers)
        assert response.status_code == 401, (method, url, response.text)
        assert response.headers["www-authenticate"] == "Bearer"
        assert isinstance(response.json()["detail"], str)

    login = auth_api.client.post("/api/auth/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    assert login.status_code == 400
    assert "khóa" in login.json()["detail"]
    assert "access_token" not in login.json()
    with auth_api.sessions() as session:
        user = session.get(User, USER_ID)
        assert user.full_name == "Recovery Test"
        assert user.password_hash == auth_api.original_hash
        assert user.is_active is False
        assert session.query(profile.Profile).filter_by(user_id=USER_ID).one().location == "Original location"
        assert session.get(User, 99).is_active is True

    # Locking one account does not invalidate the operator's session.
    assert auth_api.client.get("/api/admin/users", headers=operator_headers).status_code == 200
    unlocked = auth_api.client.patch(path, json={"is_active": True}, headers=operator_headers)
    assert unlocked.status_code == 200
    new_token = request_access_token(auth_api)
    response = auth_api.client.get("/api/users/me", headers={"Authorization": f"Bearer {new_token}"})
    assert response.status_code == 200
    assert response.json()["id"] == USER_ID
