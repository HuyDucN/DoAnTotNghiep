from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v

    @field_validator("full_name")
    @classmethod
    def name_must_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Họ tên không được để trống")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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


class ProfileUpdate(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


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


# Forward reference resolution
TokenResponse.model_rebuild()
