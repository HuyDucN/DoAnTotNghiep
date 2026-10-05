"""
Skills API — Quản lý kỹ năng chuẩn hóa
GET /skills        — Public (user đăng nhập)
POST /skills       — Admin only
PUT /skills/{id}   — Admin only
DELETE /skills/{id}— Admin only
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.skill import Skill
from app.models.user import User

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


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


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
    """Chuẩn hóa tên kỹ năng: lowercase, bỏ khoảng trắng thừa, bỏ ký tự đặc biệt."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)  # bỏ ký tự đặc biệt
    name = re.sub(r"\s+", "_", name)          # khoảng trắng → _
    return name


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[SkillResponse])
def list_skills(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Danh sách kỹ năng chuẩn hóa (có filter theo category và tìm kiếm)."""
    query = db.query(Skill)
    if category:
        query = query.filter(Skill.category == category)
    if search:
        query = query.filter(Skill.name.ilike(f"%{search}%"))
    return query.order_by(Skill.category, Skill.name).all()


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
    existing = db.query(Skill).filter(Skill.normalized_name == normalized).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Kỹ năng '{payload.name}' đã tồn tại")

    skill = Skill(
        name=payload.name.strip(),
        normalized_name=normalized,
        category=payload.category,
        description=payload.description,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Cập nhật kỹ năng."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Kỹ năng không tồn tại")

    if payload.name is not None:
        skill.name = payload.name.strip()
        skill.normalized_name = _normalize(payload.name)
    if payload.category is not None:
        if payload.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail="Category không hợp lệ")
        skill.category = payload.category
    if payload.description is not None:
        skill.description = payload.description

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=204)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Xóa kỹ năng khỏi danh sách chuẩn hóa."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Kỹ năng không tồn tại")
    db.delete(skill)
    db.commit()
