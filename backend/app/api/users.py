from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin, hash_password, verify_password
from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import (
    UserResponse, ProfileUpdate, ProfileResponse, ChangePassword,
    AccountUpdate, AccountResponse,
    UserUpdate as UpdateMe,
    UserActiveUpdate as ActiveUpdate,
)
from app.services.user_management import set_user_active

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại (lấy userId từ JWT, không từ URL)."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    payload: UpdateMe,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật thông tin cơ bản của user (full_name)."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy profile chi tiết của user."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/me/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật profile (phone, location, bio, links...)."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/account", response_model=AccountResponse)
def get_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đọc tên và hồ sơ; không tạo bản ghi khi người dùng chưa có profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return AccountResponse(
        user=UserResponse.model_validate(current_user),
        profile=ProfileResponse.model_validate(profile) if profile else None,
    )


@router.put("/me/account", response_model=AccountResponse)
def update_account(
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lưu tên và hồ sơ cùng một lần commit; lỗi được get_db rollback."""
    user = (
        db.query(User)
        .filter(User.id == current_user.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    for field, value in payload.model_dump(exclude_unset=True, exclude={"full_name"}).items():
        setattr(profile, field, value)

    db.flush()
    # Serialize before commit to avoid a second database read after saving.
    result = AccountResponse(
        user=UserResponse.model_validate(user),
        profile=ProfileResponse.model_validate(profile),
    )
    db.commit()
    return result


@router.put("/me/password")
def change_password(
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đổi mật khẩu khi đã đăng nhập — phải verify mật khẩu cũ trước."""
    user = (
        db.query(User)
        .filter(User.id == current_user.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Tài khoản không còn hoạt động. Vui lòng đăng nhập lại hoặc liên hệ quản trị viên.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}


# Admin-only account management. Role is deliberately read-only here; it is
# changed directly in the database by an operator when required.
@router.get("/admin", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/admin/{user_id}", response_model=UserResponse)
def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    return user


@router.patch("/admin/{user_id}/active", response_model=UserResponse, deprecated=True)
def update_user_active(
    user_id: int,
    payload: ActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """API cũ; dùng cùng quy tắc với PATCH /api/admin/users/{user_id}/active."""
    return set_user_active(user_id, payload.is_active, db, current_admin)
