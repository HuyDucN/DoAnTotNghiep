"""Administrator-only user management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.user import (
    UserResponse, UserActiveUpdate as ActiveUpdate, AdminUserListResponse,
    UserVerifyUpdate, AuditLogResponse, PaginatedAuditLogResponse,
    OverviewStatsResponse,
)
from app.services.stats import overview_stats as build_overview_stats
from app.models.cv import CV
from app.schemas.cv import CVResponse
from app.schemas.job import PaginatedResponse
from app.services.audit import log_audit
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


@router.patch("/users/{user_id}/verify", response_model=UserResponse)
def verify_recruiter(
    user_id: int,
    payload: UserVerifyUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """[Admin] Duyệt hoặc thu hồi quyền nhà tuyển dụng."""
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    if user.role != "recruiter":
        raise HTTPException(status_code=400, detail="Chỉ áp dụng cho tài khoản nhà tuyển dụng")
    user.is_verified = payload.is_verified
    user.token_version = (user.token_version or 0) + 1
    log_audit(
        db, current_admin.id, "recruiter.verify",
        target_type="user", target_id=user.id,
        detail={"is_verified": payload.is_verified},
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/audit-logs", response_model=PaginatedAuditLogResponse)
def list_audit_logs(
    action: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Nhật ký kiểm toán, mới nhất trước, lọc theo loại hành động."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    total = query.count()
    pages = max(1, -(-total // size))
    rows = query.offset((page - 1) * size).limit(size).all()
    items = [
        AuditLogResponse(
            id=row.id, actor_id=row.actor_id,
            actor_email=row.actor.email if row.actor else None,
            action=row.action, target_type=row.target_type, target_id=row.target_id,
            detail=row.detail, created_at=row.created_at,
        )
        for row in rows
    ]
    return PaginatedAuditLogResponse(items=items, total=total, page=page, size=size, pages=pages)


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
def delete_any_cv(
    cv_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    delete_stored_cv(cv_id, db, audit_actor_id=current_admin.id)


@router.get("/stats", response_model=OverviewStatsResponse)
def get_overview_stats(
    days: int = Query(default=7, ge=1, le=90, description="Số ngày tính dữ liệu mới"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Thống kê vận hành toàn hệ thống."""
    return build_overview_stats(db, days)
