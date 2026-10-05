from pydantic import BaseModel
from typing import Optional, List, Any
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
