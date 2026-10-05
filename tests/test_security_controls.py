from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request

from app.api.admin import ActiveUpdate, update_user_active
from app.core.rate_limit import rate_limit
from app.models.skill_gap import SkillGap


def make_request(route_path: str, client_ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": route_path,
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": (client_ip, 1234),
            "root_path": "",
            "http_version": "1.1",
            "route": SimpleNamespace(path=route_path),
        }
    )


def test_rate_limit_is_scoped_to_route_and_client_ip():
    check_limit = rate_limit(max_requests=1, window_seconds=60)
    check_limit(make_request("/api/auth/login", "192.0.2.1"))

    with pytest.raises(HTTPException) as error:
        check_limit(make_request("/api/auth/login", "192.0.2.1"))

    assert error.value.status_code == 429
    assert "Retry-After" in error.value.headers
    check_limit(make_request("/api/auth/register", "192.0.2.1"))
    check_limit(make_request("/api/auth/login", "192.0.2.2"))


class FakeQuery:
    def __init__(self, db, query_number: int):
        self.db = db
        self.query_number = query_number

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.db.target

    def with_for_update(self):
        self.db.rows_locked = True
        return self

    def all(self):
        return self.db.active_admins


class FakeSession:
    def __init__(self, target, active_admins):
        self.target = target
        self.active_admins = active_admins
        self.query_count = 0
        self.rows_locked = False
        self.committed = False

    def query(self, _model):
        self.query_count += 1
        return FakeQuery(self, self.query_count)

    def commit(self):
        self.committed = True

    def refresh(self, _entity):
        pass


def test_admin_cannot_disable_the_last_active_admin():
    target = SimpleNamespace(id=2, role="admin", is_active=True)
    db = FakeSession(target=target, active_admins=[target])

    with pytest.raises(HTTPException) as error:
        update_user_active(
            user_id=target.id,
            payload=ActiveUpdate(is_active=False),
            db=db,
            current_admin=SimpleNamespace(id=1),
        )

    assert error.value.status_code == 400
    assert db.rows_locked
    assert not db.committed


def test_admin_cannot_disable_own_account():
    admin = SimpleNamespace(id=1, role="admin", is_active=True)
    db = FakeSession(target=admin, active_admins=[admin])

    with pytest.raises(HTTPException) as error:
        update_user_active(
            user_id=admin.id,
            payload=ActiveUpdate(is_active=False),
            db=db,
            current_admin=admin,
        )

    assert error.value.status_code == 400
    assert not db.committed


def test_skill_gap_has_database_uniqueness_constraint():
    unique_keys = {
        tuple(column.name for column in constraint.columns)
        for constraint in SkillGap.__table__.constraints
        if constraint.name == "uq_skill_gap_user_cv_job"
    }

    assert ("user_id", "cv_id", "job_id") in unique_keys