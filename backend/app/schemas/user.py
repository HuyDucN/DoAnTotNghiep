import re
import unicodedata
from urllib.parse import urlsplit

from pydantic import (
    BaseModel, ConfigDict, EmailStr, HttpUrl, TypeAdapter, ValidationError,
    ValidationInfo, field_validator,
)
from typing import Optional
from datetime import datetime
from app.schemas.job import PaginatedResponse


def _has_control_characters(value: str, *, multiline: bool = False) -> bool:
    return any(
        unicodedata.category(char) in {"Cc", "Cf"}
        and not (multiline and char in "\r\n\t")
        for char in value
    )


def _validate_full_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Họ tên không được để trống")
    if len(value) > 255:
        raise ValueError("Họ tên không được quá 255 ký tự")
    if _has_control_characters(value):
        raise ValueError("Họ tên không được chứa ký tự điều khiển hoặc ký tự ẩn")
    return value


_http_url = TypeAdapter(HttpUrl)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
        return v

    @field_validator("full_name")
    @classmethod
    def name_must_not_empty(cls, v: str) -> str:
        return _validate_full_name(v)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        # Omitted fields keep their defaults; an explicitly supplied null is invalid.
        if value is None:
            raise ValueError("Họ tên không được để trống")
        return _validate_full_name(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserActiveUpdate(BaseModel):
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserListResponse(PaginatedResponse[UserResponse]):
    """Số tài khoản hoạt động trên toàn bộ kết quả tìm kiếm."""
    active_total: int


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: Optional[str] = None
    location: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


    @field_validator("phone", "location", "job_title", "bio", "linkedin_url", "github_url")
    @classmethod
    def trim_and_validate_text(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        limits = {
            "phone": 20, "location": 255, "job_title": 255,
            "bio": 2000, "linkedin_url": 500, "github_url": 500,
        }
        labels = {
            "phone": "Số điện thoại", "location": "Địa điểm", "job_title": "Chức danh",
            "bio": "Giới thiệu", "linkedin_url": "URL LinkedIn", "github_url": "URL GitHub",
        }
        field = info.field_name
        if len(value) > limits[field]:
            raise ValueError(f"{labels[field]} không được quá {limits[field]} ký tự")
        if _has_control_characters(value, multiline=field == "bio"):
            raise ValueError(f"{labels[field]} chứa ký tự điều khiển hoặc ký tự ẩn")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            digits = sum(char in "0123456789" for char in value)
            if not re.fullmatch(r"\+?[0-9 ()-]+", value) or not 7 <= digits <= 15:
                raise ValueError("Số điện thoại cần có 7–15 chữ số; chỉ dùng dấu + ở đầu, dấu cách, ngoặc hoặc gạch ngang")
        return value

    @field_validator("linkedin_url", "github_url")
    @classmethod
    def validate_profile_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        message = "Đường dẫn phải là URL http:// hoặc https:// hợp lệ, không kèm tài khoản/mật khẩu"
        if not re.match(r"^https?://", value, re.IGNORECASE) or re.search(r"\s|\\", value):
            raise ValueError(message)
        try:
            authority = urlsplit(value).netloc
            if not authority or "@" in authority:
                raise ValueError(message)
            url = _http_url.validate_python(value)
        except (ValidationError, ValueError) as error:
            raise ValueError(message) from error
        if url.username is not None or url.password is not None:
            raise ValueError(message)
        return value


class AccountUpdate(ProfileUpdate, UserUpdate):
    """Cập nhật từng phần tên và hồ sơ trong cùng một giao dịch."""


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    phone: Optional[str]
    location: Optional[str]
    job_title: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    user: UserResponse
    profile: Optional[ProfileResponse]


class ChangePassword(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu mới phải có ít nhất 8 ký tự")
        return v


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu mới phải có ít nhất 8 ký tự")
        return v


# Forward reference resolution
TokenResponse.model_rebuild()
