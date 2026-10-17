"""Kiểm tra lại quyền khi dữ liệu thay đổi sau bước xác thực ban đầu."""
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_user_access_token, get_current_admin, get_current_user
from app.models import cv, job, profile, skill, skill_gap
from app.models.user import User


PATHS = ["/api/admin/users/{user_id}/active", "/api/users/admin/{user_id}/active"]


@pytest.fixture
def management_api(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "isolated-admin-transaction-test-secret-at-least-32-characters")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    with sessions() as session:
        session.add_all([
            User(id=1, email="actor@example.com", full_name="Actor", password_hash="fixture-hash", role="admin", is_active=True),
            User(id=2, email="other-admin@example.com", full_name="Other Admin", password_hash="fixture-hash", role="admin", is_active=True),
            User(id=3, email="target@example.com", full_name="Target", password_hash="fixture-hash", role="user", is_active=True),
        ])
        session.commit()

    def test_db():
        with sessions() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app = FastAPI()
    app.include_router(admin_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    headers = {"Authorization": f"Bearer {create_user_access_token(1, 'fixture-hash')}"}
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, app=app, sessions=sessions, headers=headers)
    finally:
        engine.dispose()


def change_after_authentication(api, change, target_id=3):
    observations = []

    def initially_authorized(current_user=Depends(get_current_user), db=Depends(get_db)):
        # Validate the real JWT and original role before simulating another request's commit.
        actor = get_current_admin(current_user)
        cached_target = db.get(User, target_id)
        before = (actor.role, actor.is_active, cached_target.role, cached_target.is_active)
        with api.sessions() as writer:
            change(writer)
            writer.commit()
        # Ordinary queries could keep using these old ORM values without populate_existing.
        observations.append((before, (actor.role, actor.is_active, cached_target.role, cached_target.is_active)))
        return actor

    api.app.dependency_overrides[get_current_admin] = initially_authorized
    return observations


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("requested_active", [False, True])
@pytest.mark.parametrize("change_kind,status_code", [
    ("locked", 401), ("deleted", 401), ("user", 403), ("employer", 403),
])
def test_actor_losing_permission_after_authentication_cannot_change_target(
    management_api, path, requested_active, change_kind, status_code,
):
    api = management_api
    with api.sessions() as session:
        session.get(User, 3).is_active = not requested_active
        session.commit()

    def change_actor(writer):
        actor = writer.get(User, 1)
        if change_kind == "deleted":
            writer.delete(actor)
        elif change_kind == "locked":
            actor.is_active = False
        else:
            actor.role = change_kind

    observations = change_after_authentication(api, change_actor)
    response = api.client.patch(path.format(user_id=3), json={"is_active": requested_active}, headers=api.headers)
    assert response.status_code == status_code, response.text
    assert isinstance(response.json()["detail"], str)
    if status_code == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    assert observations == [(("admin", True, "user", not requested_active), ("admin", True, "user", not requested_active))]
    with api.sessions() as session:
        target = session.get(User, 3)
        assert target.is_active is not requested_active
        assert target.role == "user"
        assert session.get(User, 2).is_active is True
        actor = session.get(User, 1)
        if change_kind == "deleted":
            assert actor is None
        elif change_kind == "locked":
            assert actor.is_active is False
        else:
            assert actor.role == change_kind


@pytest.mark.parametrize("path", PATHS)
def test_actor_locked_after_authentication_cannot_unlock_self(management_api, path):
    def lock_actor(writer):
        writer.get(User, 1).is_active = False

    observations = change_after_authentication(management_api, lock_actor, target_id=1)
    response = management_api.client.patch(path.format(user_id=1), json={"is_active": True}, headers=management_api.headers)
    assert response.status_code == 401
    assert observations == [(("admin", True, "admin", True), ("admin", True, "admin", True))]
    with management_api.sessions() as session:
        assert session.get(User, 1).is_active is False


@pytest.mark.parametrize("path", PATHS)
def test_authorized_actor_uses_current_target_data_instead_of_cached_copy(management_api, path):
    def change_target(writer):
        target = writer.get(User, 3)
        target.role = "admin"
        target.full_name = "Renamed by another request"
        target.is_active = False

    observations = change_after_authentication(management_api, change_target)
    response = management_api.client.patch(path.format(user_id=3), json={"is_active": True}, headers=management_api.headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["role"] == "admin"
    assert data["full_name"] == "Renamed by another request"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert observations == [(("admin", True, "user", True), ("admin", True, "user", True))]
    with management_api.sessions() as session:
        target = session.get(User, 3)
        assert target.role == "admin"
        assert target.is_active is True


@pytest.mark.parametrize("path", PATHS)
def test_only_remaining_active_admin_cannot_lock_self(management_api, path):
    with management_api.sessions() as session:
        session.get(User, 2).is_active = False
        session.commit()
    response = management_api.client.patch(path.format(user_id=1), json={"is_active": False}, headers=management_api.headers)
    assert response.status_code == 400
    assert "tự khóa" in response.json()["detail"]
    with management_api.sessions() as session:
        assert session.get(User, 1).is_active is True
        assert session.query(User).filter(User.role == "admin", User.is_active.is_(True)).count() == 1


@pytest.mark.parametrize("path", PATHS)
def test_authorized_admin_can_lock_other_admin_and_unlock_them(management_api, path):
    for requested_active in (False, True):
        response = management_api.client.patch(path.format(user_id=2), json={"is_active": requested_active}, headers=management_api.headers)
        assert response.status_code == 200
        assert response.json()["is_active"] is requested_active
        with management_api.sessions() as session:
            assert session.get(User, 1).is_active is True
            assert session.get(User, 2).is_active is requested_active


@pytest.mark.parametrize("path", PATHS)
def test_authorized_admin_receives_404_for_missing_target(management_api, path):
    response = management_api.client.patch(path.format(user_id=404), json={"is_active": False}, headers=management_api.headers)
    assert response.status_code == 404
    with management_api.sessions() as session:
        assert session.get(User, 1).is_active is True
        assert session.get(User, 2).is_active is True
