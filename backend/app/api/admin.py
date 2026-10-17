"""Administrator-only user management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.user import UserResponse, UserActiveUpdate as ActiveUpdate, AdminUserListResponse
from app.models.cv import CV
from app.schemas.cv import CVResponse
from app.schemas.job import PaginatedResponse
from app.services.user_management import set_user_active
from app.services.cv_deletion import delete_stored_cv

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    page: int = Query(default=1, ge=1, description="Trang hiện tại"),
    size: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
    search: Optional[str] = None,
):
    """[Admin] Tìm theo tên/email trước khi đếm và phân trang."""
    query = db.query(User)
    keyword = (search or "").strip()
    if keyword:
        escaped = keyword.replace("/", "//").replace("%", "/%").replace("_", "/_")
        pattern = f"%{escaped}%"
        query = query.filter(or_(
            User.full_name.ilike(pattern, escape="/"),
            User.email.ilike(pattern, escape="/"),
        ))
    total = query.count()
    active_total = query.filter(User.is_active.is_(True)).count()
    pages = max(1, -(-total // size))
    page = min(page, pages)
    items = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * size).limit(size).all()
    )
    return AdminUserListResponse(
        items=items, total=total, page=page, size=size, pages=pages,
        active_total=active_total,
    )


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def update_user_active(
    user_id: int,
    payload: ActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return set_user_active(user_id, payload.is_active, db, current_admin)


@router.get("/cvs", response_model=PaginatedResponse[CVResponse])
def list_all_cvs(
    page: int = Query(default=1, ge=1, description="Trang hiện tại"),
    size: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Danh sách tất cả CV đã upload (có phân trang)."""
    query = db.query(CV).order_by(CV.created_at.desc())
    total = query.count()
    pages = max(1, -(-total // size))
    items = query.offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.delete("/cvs/{cv_id}", status_code=204)
def delete_any_cv(cv_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    delete_stored_cv(cv_id, db)
