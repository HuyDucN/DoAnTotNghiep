"""Tra cứu kỹ năng chung, tương thích tên cũ mà không gộp nhầm kỹ năng."""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.services.skill_names import normalize_skill_name, validate_skill_name


def find_skill_by_name(session: Session, name: str) -> Skill | None:
    name = validate_skill_name(name)
    normalized = normalize_skill_name(name)
    # Tên thật giúp dùng lại Node.Js có normalized_name=nodejs từ dữ liệu cũ.
    skill = session.query(Skill).filter(func.lower(Skill.name) == name.lower()).first()
    if skill is None:
        skill = session.query(Skill).filter(Skill.normalized_name == normalized).first()
    if skill is not None and normalize_skill_name(skill.name) != normalized:
        raise HTTPException(
            status_code=409,
            detail="Tên kỹ năng xung đột với dữ liệu cũ. Cần kiểm tra danh mục trước khi lưu.",
        )
    return skill


def get_or_create_skill(session: Session, name: str, category: str = "other") -> Skill:
    name = validate_skill_name(name)
    skill = find_skill_by_name(session, name)
    if skill is None:
        skill = Skill(name=name, normalized_name=normalize_skill_name(name), category=category)
        session.add(skill)
        session.flush()
    elif skill.is_deleted:
        skill.is_deleted = False
        skill.deleted_at = None
    return skill
