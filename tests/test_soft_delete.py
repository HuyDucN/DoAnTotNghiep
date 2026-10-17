from types import SimpleNamespace

from app.api.skills import SkillCreate, create_skill
from app.api.jobs import _get_or_restore_skill


class FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.row


class FakeSession:
    def __init__(self, row=None):
        self.row = row
        self.added = []
        self.flushed = False
        self.committed = False

    def query(self, _model):
        return FakeQuery(self.row)

    def add(self, entity):
        self.added.append(entity)

    def flush(self):
        self.flushed = True
        if self.added and getattr(self.added[-1], "id", None) is None:
            self.added[-1].id = 99

    def commit(self):
        self.committed = True

    def refresh(self, _entity):
        pass


def test_create_skill_restores_soft_deleted_record():
    deleted = SimpleNamespace(
        id=7,
        name="Python",
        category="other",
        description="old",
        normalized_name="python",
        is_deleted=True,
        deleted_at="2026-10-01",
    )
    db = FakeSession(deleted)

    result = create_skill(
        SkillCreate(name="Python", category="programming_language", description="language"),
        db=db,
        _=SimpleNamespace(role="admin"),
    )

    assert result is deleted
    assert deleted.is_deleted is False
    assert deleted.deleted_at is None
    assert deleted.name == "Python"
    assert deleted.category == "programming_language"
    assert db.committed


def test_job_skill_helper_restores_deleted_skill_without_inserting_duplicate():
    deleted = SimpleNamespace(name="Python", normalized_name="python", is_deleted=True, deleted_at="2026-10-01")
    db = FakeSession(deleted)

    result = _get_or_restore_skill(db, "python", "Python")

    assert result is deleted
    assert deleted.is_deleted is False
    assert deleted.deleted_at is None
    assert db.added == []
