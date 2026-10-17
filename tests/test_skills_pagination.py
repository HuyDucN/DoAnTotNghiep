from types import SimpleNamespace

from app.api.skills import list_skills


class FakeQuery:
    def __init__(self):
        self.items = [SimpleNamespace(id=21, name="Python", normalized_name="python", category="programming_language", description=None)]

    def filter(self, *_conditions):
        return self

    def order_by(self, *_columns):
        return self

    def count(self):
        return 45

    def offset(self, _value):
        return self

    def limit(self, _value):
        return self

    def all(self):
        return self.items


class FakeSession:
    def query(self, _model):
        return FakeQuery()


def test_skills_list_returns_paginated_metadata():
    result = list_skills(page=2, size=20, db=FakeSession(), _=SimpleNamespace(id=1))

    assert result.total == 45
    assert result.page == 2
    assert result.size == 20
    assert result.pages == 3
    assert len(result.items) == 1
