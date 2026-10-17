"""Danh sách quản trị phải phân trang đầy đủ và giữ phân quyền với ứng viên."""
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.jobs import router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import cv, profile, skill, skill_gap, user
from app.models.job import Job


@pytest.fixture
def admin_jobs_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    created_at = datetime(2026, 10, 1)
    session.add_all([
        Job(
            id=index, title="Developer", company="RareCo" if index == 1 else "Example",
            category="backend" if index % 2 else "frontend", created_at=created_at,
        )
        for index in range(1, 126)
    ])
    session.add_all([
        Job(
            id=index, title="Dormant Analyst", category="data",
            is_active=False, created_at=created_at,
        )
        for index in range(126, 132)
    ])
    session.add(Job(id=132, title="Deleted Job", is_deleted=True, created_at=created_at))
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


def list_admin(client, **params):
    response = client.get("/api/jobs/admin/list", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_page_through_more_than_100_jobs(admin_jobs_api):
    client, _ = admin_jobs_api
    first = list_admin(client, page=1, size=100)
    second = list_admin(client, page=2, size=100)
    assert (first["total"], first["pages"], first["active_total"], first["category_count"]) == (131, 2, 125, 3)
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == list(range(131, 0, -1))
    assert len(set(ids)) == 131


def test_admin_sees_inactive_jobs_but_candidates_do_not(admin_jobs_api):
    client, _ = admin_jobs_api
    result = list_admin(client, search="Dormant")
    assert (result["total"], result["active_total"], result["category_count"]) == (6, 0, 1)
    assert all(not job["is_active"] for job in result["items"])
    public = client.get("/api/jobs/", params={"search": "Dormant"})
    assert public.status_code == 200
    assert public.json()["total"] == 0


def test_admin_searches_company_outside_first_100_jobs(admin_jobs_api):
    client, _ = admin_jobs_api
    result = list_admin(client, search="  rareco  ")
    assert (result["total"], result["active_total"], result["category_count"]) == (1, 1, 1)
    assert [item["id"] for item in result["items"]] == [1]


def test_admin_combines_search_category_and_pagination(admin_jobs_api):
    client, _ = admin_jobs_api
    result = list_admin(client, search="Developer", category="backend", page=2, size=20)
    assert (result["total"], result["active_total"], result["category_count"], result["pages"]) == (63, 63, 1, 4)
    assert [item["id"] for item in result["items"]] == list(range(85, 46, -2))


def test_deleted_job_is_excluded_from_admin_list_and_counts(admin_jobs_api):
    client, _ = admin_jobs_api
    result = list_admin(client, search="Deleted")
    assert result["items"] == []
    assert (result["total"], result["pages"], result["active_total"], result["category_count"]) == (0, 1, 0, 0)


def test_admin_page_is_clamped_after_last_page_shrinks(admin_jobs_api):
    client, _ = admin_jobs_api
    result = list_admin(client, page=7, size=20)
    assert result["page"] == 7
    assert len(result["items"]) == 11
    for item in result["items"]:
        assert client.delete(f"/api/jobs/admin/{item['id']}").status_code == 204
    after_delete = list_admin(client, page=7, size=20)
    assert (after_delete["page"], after_delete["pages"], after_delete["total"]) == (6, 6, 120)
    assert len(after_delete["items"]) == 20


def test_created_and_updated_job_appears_in_filtered_list_with_fresh_counts(admin_jobs_api):
    client, _ = admin_jobs_api
    created = client.post("/api/jobs/admin", json={"title": "New Vacancy", "company": "NewCo", "category": "data"})
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    result = list_admin(client, search="NewCo")
    assert (result["total"], result["active_total"], result["category_count"]) == (1, 1, 1)
    assert [item["id"] for item in result["items"]] == [job_id]
    updated = client.put(f"/api/jobs/admin/{job_id}", json={
        "company": "RevisedCo", "required_skills": [{"skill_name": "Python", "importance": "high"}],
    })
    assert updated.status_code == 200, updated.text
    assert list_admin(client, search="NewCo")["total"] == 0
    revised = list_admin(client, search="RevisedCo")
    assert revised["total"] == 1
    assert revised["items"][0]["job_skills"][0]["skill_name"] == "Python"
    assert list_admin(client)["total"] == 132


@pytest.mark.parametrize("role", ["user", "employer"])
def test_non_admin_cannot_read_admin_job_list(admin_jobs_api, role):
    client, app = admin_jobs_api
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role=role)
    assert client.get("/api/jobs/admin/list").status_code == 403


def test_admin_job_list_requires_login(admin_jobs_api):
    client, app = admin_jobs_api
    del app.dependency_overrides[get_current_user]
    assert client.get("/api/jobs/admin/list").status_code == 401


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}])
def test_admin_job_list_validates_pagination(admin_jobs_api, params):
    client, _ = admin_jobs_api
    assert client.get("/api/jobs/admin/list", params=params).status_code == 422
