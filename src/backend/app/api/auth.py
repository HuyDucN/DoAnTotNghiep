from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse, ForgotPassword, ResetPassword
from datetime import timedelta
from app.core.security import decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
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

    # Tự động tạo profile rỗng
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập và trả về JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị khóa")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
@router.post("/logout")
def logout():
    """Đăng xuất. Client tự xoá token."""
    return {"message": "Đăng xuất thành công"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPassword, db: Session = Depends(get_db)):
    """Yêu cầu quên mật khẩu (Trả về dev token cho demo)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Luôn trả về thành công để tránh user enumeration
        return {"message": "Nếu email tồn tại trong hệ thống, hướng dẫn khôi phục sẽ được gửi."}

    # Tạo token riêng cho reset với purpose="reset" và hạn ngắn (15 phút)
    reset_token = create_access_token(
        data={"sub": str(user.id), "purpose": "reset"},
        expires_delta=timedelta(minutes=15)
    )
    
    # TRONG THỰC TẾ: Gửi email. TRONG BÀI TẬP: Trả về để tiện test.
    return {
        "message": "Nếu email tồn tại trong hệ thống, hướng dẫn khôi phục sẽ được gửi.",
        "devResetToken": reset_token
    }


@router.post("/reset-password")
def reset_password(payload: ResetPassword, db: Session = Depends(get_db)):
    """Đặt lại mật khẩu."""
    payload_data = decode_token(payload.token)
    if not payload_data or payload_data.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã hết hạn")

    user_id = payload_data.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Người dùng không tồn tại")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"message": "Đặt lại mật khẩu thành công"}
