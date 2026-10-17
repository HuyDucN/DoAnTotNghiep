from pydantic import BaseModel, Field, field_validator
from app.services.skill_names import validate_skill_name as validate_skill_name_value
from typing import Literal, Optional, List, Any
from datetime import datetime


class CVResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_size: Optional[int]
    status: str
    ai_analysis: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


class CVStatusResponse(BaseModel):
    """Trạng thái nhẹ cho polling khi CV đang được AI xử lý."""
    id: int
    status: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CVAnalysisResult(BaseModel):
    cv_id: int
    status: str
    skills: List[dict]
    education: List[dict]
    experience: List[dict]
    projects: List[dict]
    certificates: List[dict]


class SkillResponse(BaseModel):
    id: int
    name: str
    normalized_name: str
    category: str

    class Config:
        from_attributes = True


class CVSkillResponse(BaseModel):
    skill: SkillResponse
    proficiency_level: str
    years_experience: float

    class Config:
        from_attributes = True


class CVSkillManualRequest(BaseModel):
    skill_name: str = Field(min_length=1, max_length=255)
    proficiency_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
    years_experience: float = Field(default=0, ge=0, le=80, allow_inf_nan=False)

    @field_validator("skill_name", mode="before")
    @classmethod
    def validate_skill_name(cls, value):
        return validate_skill_name_value(value)

    @field_validator("years_experience", mode="before")
    @classmethod
    def reject_boolean_experience(cls, value):
        if isinstance(value, bool):
            raise ValueError("Số năm kinh nghiệm phải là số")
        return value


class CVSkillItemResponse(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    proficiency_level: str
    years_experience: float
    source: str
