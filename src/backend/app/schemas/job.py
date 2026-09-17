from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobSkillIn(BaseModel):
    skill_name: str
    is_required: bool = True
    importance: str = "medium"


class JobCreate(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: str = "full_time"
    level: str = "junior"
    category: str = "other"
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: List[JobSkillIn] = []
    preferred_skills: List[JobSkillIn] = []


class JobUpdate(JobCreate):
    pass


class JobSkillResponse(BaseModel):
    skill_id: int
    skill_name: str
    is_required: bool
    importance: str

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    job_type: str
    level: str
    category: str
    description: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    is_active: bool
    job_skills: List[JobSkillResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class SkillGapResponse(BaseModel):
    id: int
    match_score: float
    matched_skills: List[dict]
    missing_skills: List[dict]
    weak_skills: List[dict]
    ai_recommendation: Optional[str]
    job: "JobResponse"
    created_at: datetime

    class Config:
        from_attributes = True


SkillGapResponse.model_rebuild()
