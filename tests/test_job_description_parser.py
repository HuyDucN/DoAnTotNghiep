import json
from types import SimpleNamespace

import pytest

from app.services import ai_analyzer
from app.services.ai_analyzer import parse_job_description_with_ai


@pytest.fixture(autouse=True)
def disable_live_ai(monkeypatch):
    # Test phải độc lập với API key trên máy và không gọi dịch vụ AI thật.
    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "")


def test_local_job_description_parser_extracts_safe_structured_fields():
    result = parse_job_description_with_ai(
        "Senior Backend Developer\n"
        "Required skills: Python, FastAPI, PostgreSQL\n"
        "Salary 1500 2500"
    )

    assert result["title"] == "Senior Backend Developer"
    assert result["level"] == "senior"
    assert result["category"] == "backend"
    assert result["salary_min"] == 1500
    assert result["salary_max"] == 2500
    assert {skill["skill_name"] for skill in result["required_skills"]} >= {"Python", "Fastapi", "Postgresql"}


def skill_names(result, group):
    return {item["skill_name"].lower() for item in result[group]}


def test_skill_matching_does_not_match_substrings():
    result = parse_job_description_with_ai(
        "Frontend Developer\nRequired skills: JavaScript, MySQL, PostgreSQL\nDigital products"
    )
    assert skill_names(result, "required_skills") == {"javascript", "mysql", "postgresql"}


@pytest.mark.parametrize("description", [
    "Backend Developer\nRequired skills:\n- Python\n- SQL\nPreferred skills:\n- Docker\n- AWS",
    "Backend Developer\nRequired: Python, SQL; Preferred: Docker, AWS",
    "Backend Developer\nRequired: Python, SQL, Preferred: Docker, AWS",
    "Backend Developer\nYêu cầu:\n- Python, SQL\nƯu tiên:\n- Docker, AWS",
])
def test_required_and_preferred_follow_local_sections(description):
    result = parse_job_description_with_ai(description)
    assert skill_names(result, "required_skills") == {"python", "sql"}
    assert skill_names(result, "preferred_skills") == {"docker", "aws"}
    assert all(item["is_required"] for item in result["required_skills"])
    assert all(not item["is_required"] for item in result["preferred_skills"])


def test_duplicate_skill_is_required_when_any_section_requires_it():
    result = parse_job_description_with_ai(
        "Developer\nPreferred: Python, Docker\nRequired: Python\nPreferred: Python"
    )
    assert skill_names(result, "required_skills") == {"python"}
    assert skill_names(result, "preferred_skills") == {"docker"}


def test_optional_marker_does_not_make_skills_required():
    result = parse_job_description_with_ai("Developer\nRequired: Python\nKhông bắt buộc: Docker")
    assert skill_names(result, "required_skills") == {"python"}
    assert skill_names(result, "preferred_skills") == {"docker"}


def test_benefits_section_does_not_add_requirements():
    result = parse_job_description_with_ai(
        "Developer\nRequired: Python\nBenefits: Free AWS certification\nPreferred: Docker"
    )
    assert skill_names(result, "required_skills") == {"python"}
    assert skill_names(result, "preferred_skills") == {"docker"}


def test_unlabelled_skills_remain_preferred():
    result = parse_job_description_with_ai("Developer\nPython, SQL, Docker")
    assert result["required_skills"] == []
    assert skill_names(result, "preferred_skills") == {"python", "sql", "docker"}


@pytest.mark.parametrize("description", [
    "Developer\nRequired: Python\n3 years experience\nContact: 0901234567\nPosted 2026",
    "Developer\nRequired: Python\nSalary: negotiable\n3 years experience",
])
def test_unrelated_numbers_are_not_salary(description):
    result = parse_job_description_with_ai(description)
    assert result["salary_min"] is None
    assert result["salary_max"] is None


@pytest.mark.parametrize("salary", ["Salary: $1,500 - $2,500", "Lương: 1500–2500 USD"])
def test_salary_uses_only_explicit_salary_line(salary):
    result = parse_job_description_with_ai(f"Developer\n3 years experience\n{salary}\nContact 0901234567")
    assert (result["salary_min"], result["salary_max"]) == (1500, 2500)


def test_single_salary_and_monthly_unit_are_supported():
    result = parse_job_description_with_ai("Developer\nSalary: $1,500 per month")
    assert (result["salary_min"], result["salary_max"]) == (1500, None)


@pytest.mark.parametrize("salary", ["Lương: 20-30 triệu VND", "Salary: 2500-1500 USD"])
def test_unsupported_or_reversed_salary_is_left_empty(salary):
    result = parse_job_description_with_ai(f"Developer\n{salary}")
    assert result["salary_min"] is None
    assert result["salary_max"] is None


def test_fullstack_title_takes_priority_over_mentioned_frontend_technology():
    result = parse_job_description_with_ai("Senior Fullstack Developer\nRequired: React, Python")
    assert result["category"] == "fullstack"
    assert result["level"] == "senior"


def test_level_does_not_match_internal_or_leadership():
    result = parse_job_description_with_ai("Developer for internal tools\nTeamwork and leadership")
    assert result["level"] == "junior"


def test_provider_failure_uses_local_parser_without_network(monkeypatch):
    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "test-only")

    def unavailable():
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ai_analyzer, "_get_openai_client", unavailable)
    result = parse_job_description_with_ai("Developer\nRequired: Python\nPreferred: Docker")
    assert skill_names(result, "required_skills") == {"python"}
    assert skill_names(result, "preferred_skills") == {"docker"}


def test_valid_ai_response_keeps_existing_provider_flow(monkeypatch):
    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "test-only")
    response_data = {"title": "AI result", "company": "Example", "level": "senior"}
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(response_data)),
    )])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
    monkeypatch.setattr(ai_analyzer, "_get_openai_client", lambda: client)
    result = parse_job_description_with_ai("Developer\nRequired: Python")
    assert result["title"] == "AI result"
    assert result["company"] == "Example"


def test_invalid_ai_json_falls_back_to_local_parser(monkeypatch):
    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "test-only")
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="invalid JSON"))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
    monkeypatch.setattr(ai_analyzer, "_get_openai_client", lambda: client)
    result = parse_job_description_with_ai("Developer\nRequired: Python\nPreferred: Docker")
    assert skill_names(result, "required_skills") == {"python"}
    assert skill_names(result, "preferred_skills") == {"docker"}
