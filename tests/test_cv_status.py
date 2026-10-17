from types import SimpleNamespace

from fastapi import HTTPException

from app.api.cv import _get_analysis_lock, get_cv_status


class FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.row


class FakeSession:
    def __init__(self, row):
        self.row = row

    def query(self, _model):
        return FakeQuery(self.row)


def test_cv_status_returns_only_processing_metadata():
    cv = SimpleNamespace(id=12, user_id=4, status="processing", updated_at=None)

    result = get_cv_status(12, SimpleNamespace(id=4), FakeSession(cv))

    assert result.id == 12
    assert result.status == "processing"
    assert result.updated_at is None


def test_cv_status_hides_cv_owned_by_another_user():
    with_user = SimpleNamespace(id=12, user_id=9, status="analyzed", updated_at=None)

    # The real query applies the owner condition; this fake models the
    # resulting empty query when the owner does not match.
    class OwnerAwareSession(FakeSession):
        def query(self, _model):
            return FakeQuery(None)

    try:
        get_cv_status(12, SimpleNamespace(id=4), OwnerAwareSession(with_user))
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Expected a 404 for a CV owned by another user")


def test_same_file_hash_uses_one_shared_analysis_lock():
    first = _get_analysis_lock("same-file-hash")
    second = _get_analysis_lock("same-file-hash")

    assert first is second
    assert first.acquire(blocking=False)
    try:
        assert not second.acquire(blocking=False)
    finally:
        first.release()
