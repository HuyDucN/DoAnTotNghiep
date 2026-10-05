from types import SimpleNamespace

from app.services.skill_matcher import calculate_match_score


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
