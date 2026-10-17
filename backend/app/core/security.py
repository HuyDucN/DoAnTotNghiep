from datetime import datetime, timedelta
import hashlib
import hmac
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"purpose": "access", **data}
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        if any(type(payload[claim]) is not int for claim in ("exp", "iat", "nbf") if claim in payload):
            return None
        return payload
    except (JWTError, TypeError, ValueError, OverflowError):
        return None


def token_user_id(payload: Optional[dict], expected_purpose: str) -> Optional[int]:
    """Only accept IDs representable by the users table's signed INT key."""
    if not payload or payload.get("purpose") != expected_purpose:
        return None
    subject = payload.get("sub")
    if (
        not isinstance(subject, str)
        or not 1 <= len(subject) <= 10
        or not subject.isascii()
        or not subject.isdecimal()
    ):
        return None
    user_id = int(subject)
    return user_id if 1 <= user_id <= 2_147_483_647 else None


def _password_version(user_id: int, password_hash: str, purpose: str) -> str:
    # Separate domains prevent exchanging access and recovery password proofs.
    message = f"{purpose}:{user_id}:{password_hash}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def create_user_access_token(user_id: int, password_hash: str) -> str:
    return create_access_token(
        {
            "sub": str(user_id),
            "password_version": _password_version(user_id, password_hash, "access"),
        },
    )


def create_password_reset_token(user_id: int, password_hash: str) -> str:
    return create_access_token(
        {
            "sub": str(user_id),
            "purpose": "reset",
            "password_version": _password_version(user_id, password_hash, "password-reset"),
        },
        expires_delta=timedelta(minutes=15),
    )


def _token_password_matches(payload: dict, user_id: int, password_hash: str, purpose: str) -> bool:
    version = payload.get("password_version")
    domain = "password-reset" if purpose == "reset" else purpose
    return (
        token_user_id(payload, purpose) == user_id
        and isinstance(version, str)
        and len(version) == 64
        and version.isascii()
        and hmac.compare_digest(version, _password_version(user_id, password_hash, domain))
    )


def password_reset_token_matches(payload: dict, user_id: int, password_hash: str) -> bool:
    return _token_password_matches(payload, user_id, password_hash, "reset")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """FastAPI dependency — decodes JWT and returns current user."""
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    user_id = token_user_id(payload, "access")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).populate_existing().first()
    if user is None or not _token_password_matches(payload, user.id, user.password_hash, "access"):
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền admin")
    return current_user


def get_current_employer(current_user=Depends(get_current_user)):
    """Dependency cho các endpoint chỉ dành cho Nhà tuyển dụng."""
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Chỉ tài khoản nhà tuyển dụng mới có quyền này")
    return current_user
