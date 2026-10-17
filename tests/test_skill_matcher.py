from types import SimpleNamespace

import pytest

from app.services.skill_matcher import calculate_match_score
from app.api.jobs import _repair_mojibake


class Query:
    def __init__(self, rows):
        self.rows = rows

    def join(self, *_):
        return self

    def filter(self, *_):
        return self

    def all(self):
        return self.rows


class DB:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_):
        return Query(self.rows)


def skill(name, required=True, importance="high"):
    s = SimpleNamespace(id=1, name=name, normalized_name=name.lower())
    return SimpleNamespace(skill=s, skill_id=1, is_required=required, importance=importance)


def test_required_skill_match_uses_job_level():
    cv_skill = SimpleNamespace(
        skill=SimpleNamespace(id=1, name="Python", normalized_name="python"),
        proficiency_level="intermediate",
        years_experience=1,
    )
    cv = SimpleNamespace(id=1)
    job = SimpleNamespace(level="senior", job_skills=[skill("Python")])
    result = calculate_match_score(cv, job, DB([cv_skill]))
    assert result["weak_skills"][0]["needed_level"] == "advanced"
    assert result["match_score"] == 0.0


def test_missing_required_skill_is_high_priority():
    cv = SimpleNamespace(id=1)
    job = SimpleNamespace(level="junior", job_skills=[skill("Python")])
    result = calculate_match_score(cv, job, DB([]))
    assert result["missing_skills"][0]["priority"] == "high"


def test_match_score_uses_importance_weights_within_required_and_preferred_groups():
    cv_skill = SimpleNamespace(
        skill=SimpleNamespace(id=1, name="Python", normalized_name="python"),
        proficiency_level="intermediate",
        years_experience=2,
    )
    cv = SimpleNamespace(id=1)
    job = SimpleNamespace(
        level="junior",
        job_skills=[
            skill("Python", required=True, importance="high"),
            skill("Docker", required=False, importance="low"),
        ],
    )

    result = calculate_match_score(cv, job, DB([cv_skill]))

    assert result["match_score"] == 83.3


@pytest.mark.parametrize("old_level,locked_level,expected_score", [
    ("beginner", "advanced", 100),
    ("advanced", None, 0),
])
def test_locked_skill_values_override_older_database_snapshot(old_level, locked_level, expected_score):
    def cv_skill(level):
        return SimpleNamespace(
            skill=SimpleNamespace(id=1, name="Python"), proficiency_level=level,
            years_experience=2, source="manual",
        )

    cv = SimpleNamespace(id=1)
    job = SimpleNamespace(level="senior", job_skills=[skill("Python")])
    old_database_snapshot = DB([cv_skill(old_level)])
    locked_rows = [cv_skill(locked_level)] if locked_level else []
    result = calculate_match_score(cv, job, old_database_snapshot, cv_skills=locked_rows)
    assert result["match_score"] == expected_score


def test_repair_mojibake_restores_old_vietnamese_recommendation():
    old_value = "B\u00e1\u00ba\u00a1n \u00c4\u2018ang thi\u00e1\u00ba\u00bfu m\u00e1\u00bb\u2122t s\u00e1\u00bb\u2018 k\u00e1\u00bb\u00b9 n\u00c4\u0192ng"
    assert _repair_mojibake(old_value) == "B\u1ea1n \u0111ang thi\u1ebfu m\u1ed9t s\u1ed1 k\u1ef9 n\u0103ng"

