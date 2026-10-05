"""Administrator-only user management endpoints."""

from typing import List

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.user import UserResponse
from app.models.cv import CV
from app.schemas.cv import CVResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


class ActiveUpdate(BaseModel):
    is_active: bool


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def update_user_active(
    user_id: int,
    payload: ActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    if current_admin.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản admin")
    if user.role == "admin" and user.is_active and not payload.is_active:
        active_admins = db.query(User).filter(
            User.role == "admin",
            User.is_active.is_(True),
        ).with_for_update().all()
        if len(active_admins) <= 1:
            raise HTTPException(status_code=400, detail="Không thể khóa admin hoạt động cuối cùng")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/cvs", response_model=List[CVResponse])
def list_all_cvs(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    """List every uploaded CV for the admin console."""
    return db.query(CV).order_by(CV.created_at.desc()).all()


@router.delete("/cvs/{cv_id}", status_code=204)
def delete_any_cv(cv_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cv = db.query(CV).filter(CV.id == cv_id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.file_path and os.path.exists(cv.file_path):
        os.remove(cv.file_path)
    db.delete(cv)
    db.commit()
