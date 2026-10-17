"""
Skills API — Quản lý kỹ năng chuẩn hóa
GET /skills        — Public (user đăng nhập)
POST /skills       — Admin only
PUT /skills/{id}   — Admin only
DELETE /skills/{id}— Admin only
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.skill import Skill
from app.models.user import User
from app.schemas.job import PaginatedResponse
from app.services.skill_names import normalize_skill_name, validate_skill_name
from app.services.skill_catalog import find_skill_by_name

router = APIRouter(prefix="/skills", tags=["Skills"])


# ── Schemas ─────────────────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "programming_language", "framework", "database",
    "cloud", "devops", "ai_ml", "soft_skill", "tool", "other",
]


class SkillCreate(BaseModel):
    name: str
    category: str = "other"
    description: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def check_name(cls, value):
        return validate_skill_name(value)


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def check_name(cls, value):
        return validate_skill_name(value) if value is not None else None


class SkillResponse(BaseModel):
    id: int
    name: str
    normalized_name: str
    category: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    return normalize_skill_name(name)


def _commit_skill(db: Session, skill: Skill) -> Skill:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tên kỹ năng đã tồn tại hoặc xung đột với dữ liệu khác.") from exc
    db.refresh(skill)
    return skill


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedResponse[SkillResponse])
def list_skills(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Trang hiện tại"),
    size: int = Query(default=20, ge=1, le=100, description="Số kỹ năng mỗi trang"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Danh sách kỹ năng chuẩn hóa có filter và phân trang."""
    query = db.query(Skill).filter(Skill.is_deleted == False)
    if category:
        query = query.filter(Skill.category == category)
    if search:
        query = query.filter(Skill.name.ilike(f"%{search}%"))
    query = query.order_by(Skill.category, Skill.name)
    total = query.count()
    pages = max(1, -(-total // size))
    items = query.offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("/", response_model=SkillResponse, status_code=201)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Thêm kỹ năng mới vào danh sách chuẩn hóa."""
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Category không hợp lệ. Chọn một trong: {', '.join(VALID_CATEGORIES)}")

    normalized = _normalize(payload.name)
    existing = find_skill_by_name(db, payload.name)
    if existing:
        if not existing.is_deleted:
            raise HTTPException(status_code=400, detail=f"Kỹ năng '{payload.name}' đã tồn tại")

        # Tên kỹ năng vẫn bị ràng buộc UNIQUE dù bản ghi đã xóa mềm.
        # Khôi phục bản ghi cũ giúp giữ nguyên các liên kết CV/Job lịch sử.
        existing.name = payload.name.strip()
        existing.category = payload.category
        existing.description = payload.description
        existing.is_deleted = False
        existing.deleted_at = None
        return _commit_skill(db, existing)

    skill = Skill(
        name=payload.name.strip(),
        normalized_name=normalized,
        category=payload.category,
        description=payload.description,
    )
    db.add(skill)
    return _commit_skill(db, skill)


@router.put("/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Cập nhật kỹ năng."""
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.is_deleted == False).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Kỹ năng không tồn tại")

    if payload.name is not None:
        existing = find_skill_by_name(db, payload.name)
        if existing is not None and existing.id != skill.id:
            raise HTTPException(status_code=409, detail="Tên kỹ năng đã tồn tại trong danh mục.")
        skill.name = payload.name.strip()
        skill.normalized_name = _normalize(payload.name)
    if payload.category is not None:
        if payload.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail="Category không hợp lệ")
        skill.category = payload.category
    if payload.description is not None:
        skill.description = payload.description

    return _commit_skill(db, skill)


@router.delete("/{skill_id}", status_code=204)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Xóa mềm kỹ năng (Soft Delete — bảo toàn dữ liệu liên kết)."""
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.is_deleted == False).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Kỹ năng không tồn tại")
    skill.is_deleted = True
    skill.deleted_at = datetime.now(timezone.utc)
    db.commit()
