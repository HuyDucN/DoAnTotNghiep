"""Tìm kiếm trên toàn bộ dữ liệu trước khi đếm và phân trang."""
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
def jobs_search_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    created_at = datetime(2026, 10, 1)
    session.add_all([
        Job(
            id=index,
            title="Python Developer" if index <= 12 else "Other Developer",
            company="Acme Labs" if index <= 12 else "Other Company",
            level="senior" if index % 2 else "junior",
            category="backend" if index % 2 else "frontend",
            created_at=created_at,
        )
        for index in range(1, 26)
    ])
    session.add_all([
        Job(id=26, title="Python Developer", company="Acme Labs", is_active=False, created_at=created_at),
        Job(id=27, title="Python Developer", company="Acme Labs", is_deleted=True, created_at=created_at),
        Job(id=28, title="No Company Developer", company=None, created_at=created_at),
        Job(id=29, title="Growth 100%", company="a_b/Team", created_at=created_at),
        Job(id=30, title="Growth 1000", company="axb Team", created_at=created_at),
    ])
    session.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        session.close()
        engine.dispose()


def get_jobs(client, **params):
    response = client.get("/api/jobs/", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_search_finds_jobs_outside_the_unfiltered_first_page(jobs_search_api):
    first_page = get_jobs(jobs_search_api, size=10)
    assert all(item["id"] > 12 for item in first_page["items"])
    result = get_jobs(jobs_search_api, search="python", size=10)
    assert result["total"] == 12
    assert len(result["items"]) == 10
    assert all(item["id"] <= 12 for item in result["items"])


@pytest.mark.parametrize("search", ["pYtHoN", "Acme", "  Acme Labs  "])
def test_search_matches_title_or_company_and_trims_spaces(jobs_search_api, search):
    result = get_jobs(jobs_search_api, search=search, size=100)
    assert result["total"] == 12
    assert {item["id"] for item in result["items"]} == set(range(1, 13))


def test_pagination_metadata_and_order_apply_to_filtered_results(jobs_search_api):
    pages = [get_jobs(jobs_search_api, search="Acme", size=5, page=page) for page in (1, 2, 3)]
    for page, result in enumerate(pages, start=1):
        assert (result["total"], result["page"], result["size"], result["pages"]) == (12, page, 5, 3)
    assert [[item["id"] for item in result["items"]] for result in pages] == [
        [12, 11, 10, 9, 8], [7, 6, 5, 4, 3], [2, 1],
    ]


def test_search_combines_with_level_and_category(jobs_search_api):
    result = get_jobs(jobs_search_api, search="Acme", level="senior", category="backend", size=100)
    assert result["total"] == 6
    assert {item["id"] for item in result["items"]} == {1, 3, 5, 7, 9, 11}
    empty = get_jobs(jobs_search_api, search="Acme", level="senior", category="frontend")
    assert empty["total"] == 0
    assert empty["items"] == []


@pytest.mark.parametrize("search", ["%", "_", "/"])
def test_search_treats_like_metacharacters_as_literal_text(jobs_search_api, search):
    result = get_jobs(jobs_search_api, search=search)
    assert result["total"] == 1
    assert [item["id"] for item in result["items"]] == [29]


def test_blank_search_equals_no_filter_and_allows_missing_company(jobs_search_api):
    unfiltered = get_jobs(jobs_search_api, size=100)
    blank = get_jobs(jobs_search_api, search="   ", size=100)
    assert blank == unfiltered
    assert blank["total"] == 28
    result = get_jobs(jobs_search_api, search="No Company")
    assert [item["id"] for item in result["items"]] == [28]


def test_search_without_matches_has_empty_pagination(jobs_search_api):
    result = get_jobs(jobs_search_api, search="does not exist")
    assert result["total"] == 0
    assert result["pages"] == 1
    assert result["items"] == []
