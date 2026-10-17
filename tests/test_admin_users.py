"""Tìm tài khoản trên toàn bộ dữ liệu, phân trang và kiểm tra quyền quản trị."""
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import cv, job, profile, skill, skill_gap
from app.models.user import User


@pytest.fixture
def admin_users_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    created_at = datetime(2026, 10, 1)
    session.add_all([
        User(
            id=index, email=f"person{index}@example.test", password_hash="secret-hash",
            full_name="Needle Member" if index in {1, 5, 9} else f"Member {index}",
            role="admin" if index in {1, 2} else "employer" if index == 3 else "user",
            is_active=index % 3 != 0, created_at=created_at,
        )
        for index in range(1, 46)
    ])
    session.add_all([
        User(id=46, email="percent@example.test", full_name="Percent%Name", password_hash="secret", created_at=created_at),
        User(id=47, email="underscore@example.test", full_name="Underscore_Name", password_hash="secret", created_at=created_at),
        User(id=48, email="slash@example.test", full_name="Slash/Name", password_hash="secret", created_at=created_at),
    ])
    session.commit()

    def test_db():
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="admin")
    try:
        with TestClient(app) as client:
            yield client, app
    finally:
        session.close()
        engine.dispose()


def list_users(client, **params):
    response = client.get("/api/admin/users", params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("search,expected_ids", [
    ("needle", [9, 5, 1]),
    ("  NEEDLE  ", [9, 5, 1]),
    ("PERSON7@EXAMPLE.TEST", [7]),
])
def test_search_finds_name_or_email_across_all_pages(admin_users_api, search, expected_ids):
    client, _ = admin_users_api
    result = list_users(client, search=search)
    assert result["total"] == len(expected_ids)
    assert [item["id"] for item in result["items"]] == expected_ids


def test_filtered_pagination_and_counts_cover_all_matches(admin_users_api):
    client, _ = admin_users_api
    first = list_users(client, search="needle", size=2, page=1)
    second = list_users(client, search="needle", size=2, page=2)
    assert (first["total"], first["pages"], first["active_total"]) == (3, 2, 2)
    assert (second["total"], second["pages"], second["active_total"]) == (3, 2, 2)
    assert [item["id"] for item in first["items"]] == [9, 5]
    assert [item["id"] for item in second["items"]] == [1]


def test_global_counts_are_independent_of_page_size_and_hide_passwords(admin_users_api):
    client, _ = admin_users_api
    result = list_users(client, size=1)
    assert (result["total"], result["active_total"], result["pages"]) == (48, 33, 48)
    assert len(result["items"]) == 1
    assert "password_hash" not in result["items"][0]


@pytest.mark.parametrize("search,expected_id", [("%", 46), ("_", 47), ("/", 48)])
def test_search_escapes_sql_like_metacharacters(admin_users_api, search, expected_id):
    client, _ = admin_users_api
    result = list_users(client, search=search)
    assert result["total"] == 1
    assert result["items"][0]["id"] == expected_id


def test_whitespace_search_is_equivalent_to_no_filter(admin_users_api):
    client, _ = admin_users_api
    assert list_users(client, search="   ") == list_users(client)


def test_empty_search_result_has_zero_counts(admin_users_api):
    client, _ = admin_users_api
    result = list_users(client, search="no matching account")
    assert result["items"] == []
    assert (result["total"], result["active_total"], result["pages"]) == (0, 0, 1)


def test_out_of_range_page_returns_last_valid_page(admin_users_api):
    client, _ = admin_users_api
    result = list_users(client, page=100, size=20)
    assert (result["page"], result["pages"], len(result["items"])) == (3, 3, 8)


def test_lock_and_unlock_refresh_active_counts_without_losing_search_results(admin_users_api):
    client, _ = admin_users_api
    for is_active, expected_count in [(False, 32), (True, 33)]:
        response = client.patch("/api/admin/users/4/active", json={"is_active": is_active})
        assert response.status_code == 200, response.text
        assert list_users(client)["active_total"] == expected_count
        filtered = list_users(client, search="person4@example.test")
        assert filtered["total"] == 1
        assert filtered["items"][0]["is_active"] is is_active


def test_admin_still_cannot_lock_own_account(admin_users_api):
    client, _ = admin_users_api
    response = client.patch("/api/admin/users/1/active", json={"is_active": False})
    assert response.status_code == 400
    assert list_users(client, search="person1@example.test")["items"][0]["is_active"] is True


@pytest.mark.parametrize("role", ["user", "employer"])
def test_user_management_requires_admin_role(admin_users_api, role):
    client, app = admin_users_api
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4, role=role)
    assert client.get("/api/admin/users").status_code == 403
    assert client.patch("/api/admin/users/5/active", json={"is_active": False}).status_code == 403


def test_user_list_requires_login(admin_users_api):
    client, app = admin_users_api
    del app.dependency_overrides[get_current_user]
    assert client.get("/api/admin/users").status_code == 401


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}])
def test_user_list_rejects_invalid_pagination(admin_users_api, params):
    client, _ = admin_users_api
    assert client.get("/api/admin/users", params=params).status_code == 422
