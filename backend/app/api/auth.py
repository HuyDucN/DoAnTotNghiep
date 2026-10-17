from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_user_access_token, create_password_reset_token,
    decode_token, token_user_id, password_reset_token_matches,
)
from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse, ForgotPassword, ResetPassword
from app.core.config import settings
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(5, 60)),
):
    """Đăng ký tài khoản mới."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()

    # Tự động tạo hồ sơ trống.
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_user_access_token(user.id, user.password_hash)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(5, 60)),
):
    """Đăng nhập và trả về JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị khóa")

    token = create_user_access_token(user.id, user.password_hash)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
@router.post("/logout")
def logout():
    """Đăng xuất. Client tự xóa token."""
    return {"message": "Đăng xuất thành công"}



@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPassword,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(3, 60)),
):
    user = db.query(User).filter(User.email == payload.email).first()
    response = {"message": "If the email exists, recovery instructions will be sent."}
    if not user or not user.is_active:
        return response
    reset_token = create_password_reset_token(user.id, user.password_hash)
    if settings.ALLOW_DEV_RESET_TOKEN and settings.ENVIRONMENT.lower() not in {"production", "prod"}:
        response["devResetToken"] = reset_token
    return response


@router.post("/reset-password")
def reset_password(
    payload: ResetPassword,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(5, 60)),
):
    """Đặt lại mật khẩu."""
    payload_data = decode_token(payload.token)
    invalid_token = HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã hết hạn")
    user_id = token_user_id(payload_data, "reset")
    if user_id is None:
        raise invalid_token

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if (
        not user
        or not user.is_active
        or not password_reset_token_matches(payload_data, user.id, user.password_hash)
    ):
        raise invalid_token

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"message": "Đặt lại mật khẩu thành công", "user_id": user.id}
