"""Quy tắc chung cho thao tác khóa và mở khóa tài khoản."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User


def set_user_active(
    user_id: int,
    is_active: bool,
    db: Session,
    current_admin: User,
) -> User:
    actor_id = current_admin.id
    # Read current row values while holding locks, even if authentication already
    # loaded an older copy into this session's identity map.
    admins = (
        db.query(User)
        .filter(User.role == "admin")
        .order_by(User.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    actor = (
        db.query(User)
        .filter(User.id == actor_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if actor is None or not actor.is_active:
        raise HTTPException(
            status_code=401,
            detail="Tài khoản không còn hoạt động. Vui lòng đăng nhập lại hoặc liên hệ quản trị viên.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền admin")

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

    if user.id == actor_id and not is_active:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản admin")

    if user.role == "admin" and user.is_active and not is_active:
        if sum(bool(admin.is_active) for admin in admins) <= 1:
            raise HTTPException(status_code=400, detail="Không thể khóa admin hoạt động cuối cùng")

    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
