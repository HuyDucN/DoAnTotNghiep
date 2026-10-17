"""Thông tin liên hệ được đọc cục bộ, không lấy từ kết quả AI."""
import json
from types import SimpleNamespace

import pytest

from app.services import ai_analyzer


@pytest.fixture
def fake_ai(monkeypatch):
    calls = []
    payload = {
        "email": "invented@example.test", "phone": "+84999999999",
        "summary": "Backend developer", "skills": [],
    }

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(payload)),
        )])

    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(ai_analyzer, "_get_openai_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    ))
    monkeypatch.setattr(ai_analyzer.time, "sleep", lambda _: None)
    return calls, payload


@pytest.mark.parametrize("phone,expected", [
    ("0901234567", "0901234567"),
    ("090 123 4567", "0901234567"),
    ("090.123.4567", "0901234567"),
    ("+84 901 234 567", "+84901234567"),
    ("+84 (0) 901 234 567", "+84901234567"),
    ("0084 901 234 567", "+84901234567"),
    ("(028) 3822 3344", "02838223344"),
    ("+1 (415) 555-2671", "+14155552671"),
])
def test_analysis_merges_local_email_and_phone_instead_of_ai_values(fake_ai, phone, expected):
    calls, _ = fake_ai
    result = ai_analyzer.analyze_cv_with_ai(f"Email: candidate+cv@example.test\nPhone: {phone}\nPython developer")
    assert result is not None
    assert result["email"] == "candidate+cv@example.test"
    assert result["phone"] == expected
    sent = calls[0]["messages"][1]["content"]
    assert "candidate+cv@example.test" not in sent
    assert phone not in sent
    assert "[EMAIL]" in sent
    assert "[PHONE]" in sent


def test_missing_contacts_do_not_accept_invented_ai_contacts(fake_ai):
    result = ai_analyzer.analyze_cv_with_ai("Python developer\nExperience: 2019 - 2023")
    assert result["email"] == ""
    assert result["phone"] == ""


def test_contacts_are_read_from_full_cv_before_ai_input_is_truncated(fake_ai):
    calls, _ = fake_ai
    result = ai_analyzer.analyze_cv_with_ai("x" * 13000 + "\nEmail: last@example.test\nPhone: 0901234567")
    assert result["email"] == "last@example.test"
    assert result["phone"] == "0901234567"
    sent_cv = json.loads(calls[0]["messages"][1]["content"])["cv_text"]
    assert len(sent_cv) <= 12000


def test_redaction_happens_before_truncation_at_email_boundary(fake_ai):
    calls, _ = fake_ai
    result = ai_analyzer.analyze_cv_with_ai("x" * 11994 + "\nalice@example.test\nPython")
    sent_cv = json.loads(calls[0]["messages"][1]["content"])["cv_text"]
    assert result["email"] == "alice@example.test"
    assert "alice" not in sent_cv


def test_redaction_preserves_dates_salary_and_experience_ranges(fake_ai):
    calls, _ = fake_ai
    cv_text = "Education: 2019 - 2023\nExperience: 2023-2026\nSalary: 1500 - 2500\n3 years Python"
    ai_analyzer.analyze_cv_with_ai(cv_text)
    sent_cv = json.loads(calls[0]["messages"][1]["content"])["cv_text"]
    assert sent_cv == cv_text


def test_all_supported_contacts_are_redacted_and_first_contact_is_selected(fake_ai):
    calls, _ = fake_ai
    result = ai_analyzer.analyze_cv_with_ai(
        "first@example.test, second@example.test\n0901234567 0912345678"
    )
    sent_cv = json.loads(calls[0]["messages"][1]["content"])["cv_text"]
    assert result["email"] == "first@example.test"
    assert result["phone"] == "0901234567"
    for contact in ("first@example.test", "second@example.test", "0901234567", "0912345678"):
        assert contact not in sent_cv


def test_phone_like_email_username_is_not_extracted_as_phone(fake_ai):
    result = ai_analyzer.analyze_cv_with_ai("Email: 0901234567@example.test\nPython")
    assert result["email"] == "0901234567@example.test"
    assert result["phone"] == ""


def test_contact_fields_from_ai_are_overridden_before_schema_validation(fake_ai):
    _, payload = fake_ai
    payload.update({"email": None, "phone": ["untrusted value"]})
    result = ai_analyzer.analyze_cv_with_ai("Email: actual@example.test\nPhone: 0901234567")
    assert result is not None
    assert result["email"] == "actual@example.test"
    assert result["phone"] == "0901234567"


def test_non_phone_identifiers_are_not_used_as_contact_numbers(fake_ai):
    result = ai_analyzer.analyze_cv_with_ai("Employee ID: 123456789012\naccount0901234567suffix\nPython")
    assert result["phone"] == ""


def test_no_api_key_still_returns_analysis_failure_without_fake_success(fake_ai, monkeypatch):
    calls, _ = fake_ai
    monkeypatch.setattr(ai_analyzer.settings, "OPENAI_API_KEY", "")
    assert ai_analyzer.analyze_cv_with_ai("Email: candidate@example.test") is None
    assert calls == []


def test_recommendation_redacts_contacts_from_existing_summary(fake_ai):
    calls, _ = fake_ai
    ai_analyzer.generate_recommendation(
        {"summary": "Developer candidate@example.test, phone 0901234567"},
        [{"skill_name": "Docker", "priority": "high"}],
        "Backend Developer",
    )
    sent = calls[0]["messages"][1]["content"]
    assert "candidate@example.test" not in sent
    assert "0901234567" not in sent
    assert "Docker" in sent


def test_cached_analysis_refreshes_contacts_from_raw_text(fake_ai, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.api import cv as cv_api
    from app.core import database
    from app.models import job, profile, skill, skill_gap
    from app.models.cv import CV
    from app.models.user import User

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    database.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    raw_text = "Email: actual@example.test\nPhone: 0901234567\nPython"
    with factory() as session:
        session.add(User(id=4, email="owner@example.test", full_name="Owner", password_hash="test"))
        session.add_all([
            CV(id=1, user_id=4, filename="cached.pdf", file_path="cached.pdf", status="analyzed",
               file_hash="same-contact-test-hash", raw_text=raw_text,
               ai_analysis={"email": "wrong@example.test", "phone": "[PHONE]", "skills": []}),
            CV(id=2, user_id=4, filename="new.pdf", file_path="new.pdf", status="uploaded",
               file_hash="same-contact-test-hash"),
        ])
        session.commit()
    monkeypatch.setattr(database, "SessionLocal", factory)
    try:
        cv_api.process_cv_analysis(2, "new.pdf")
        with factory() as session:
            result = session.get(CV, 2)
            assert result.status == "analyzed"
            assert result.ai_analysis["email"] == "actual@example.test"
            assert result.ai_analysis["phone"] == "0901234567"
            assert session.get(CV, 1).ai_analysis["email"] == "wrong@example.test"
        assert fake_ai[0] == []
    finally:
        engine.dispose()
