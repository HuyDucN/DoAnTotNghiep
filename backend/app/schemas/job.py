from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List, Literal, Generic, TypeVar
from datetime import datetime, timezone
from app.services.skill_names import validate_skill_name
from app.services.cv_match_state import CvMatchStatus

T = TypeVar("T")


class JobSkillIn(BaseModel):
    skill_name: str
    is_required: bool = True
    importance: Literal["high", "medium", "low"] = "medium"

    @field_validator("skill_name", mode="before")
    @classmethod
    def check_skill_name(cls, value):
        return validate_skill_name(value)


class JobCreate(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Literal["full_time", "part_time", "internship", "freelance"] = "full_time"
    level: Literal["intern", "fresher", "junior", "mid", "senior", "lead"] = "junior"
    category: Literal["backend", "frontend", "fullstack", "data", "ai_ml", "devops", "mobile", "qa", "other"] = "other"
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: List[JobSkillIn] = []
    preferred_skills: List[JobSkillIn] = []


class JobUpdate(BaseModel):
    """Chỉ cập nhật trường được gửi lên; [] xóa một nhóm kỹ năng."""

    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[Literal["full_time", "part_time", "internship", "freelance"]] = None
    level: Optional[Literal["intern", "fresher", "junior", "mid", "senior", "lead"]] = None
    category: Optional[Literal["backend", "frontend", "fullstack", "data", "ai_ml", "devops", "mobile", "qa", "other"]] = None
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: Optional[List[JobSkillIn]] = None
    preferred_skills: Optional[List[JobSkillIn]] = None

    @field_validator("title", "job_type", "level", "category", "required_skills", "preferred_skills")
    @classmethod
    def reject_explicit_null(cls, value):
        # Validator không chạy cho trường bị bỏ qua. Null được gửi rõ ràng
        # không có nghĩa là giữ nguyên hoặc xóa nhóm kỹ năng (hãy dùng []).
        if value is None:
            raise ValueError("Trường này không nhận null; bỏ qua để giữ nguyên hoặc dùng [] cho danh sách kỹ năng")
        return value


class JobDescriptionParseRequest(BaseModel):
    description: str = Field(min_length=20, max_length=20000)


class JobDescriptionParseResponse(BaseModel):
    title: str = ""
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Literal["full_time", "part_time", "internship", "freelance"] = "full_time"
    level: Literal["intern", "fresher", "junior", "mid", "senior", "lead"] = "junior"
    category: Literal["backend", "frontend", "fullstack", "data", "ai_ml", "devops", "mobile", "qa", "other"] = "other"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: List[JobSkillIn] = Field(default_factory=list)
    preferred_skills: List[JobSkillIn] = Field(default_factory=list)


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


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema phân trang chuẩn cho mọi danh sách."""
    items: List[T]
    total: int       # Tổng số bản ghi (không filter pagination)
    page: int        # Trang hiện tại (bắt đầu từ 1)
    size: int        # Số bản ghi mỗi trang
    pages: int       # Tổng số trang


class AdminJobListResponse(PaginatedResponse[JobResponse]):
    """Thống kê trên toàn bộ kết quả lọc, không chỉ trang hiện tại."""
    active_total: int
    category_count: int


class SkillGroupScore(BaseModel):
    importance: Literal["high", "medium", "low"]
    matched_weight: float
    total_weight: float
    score: float


class SkillGapResponse(BaseModel):
    id: int
    cv_id: int
    cv_filename: str
    cv_match_status: CvMatchStatus = "unknown"
    match_score: float
    matched_skills: List[dict]
    missing_skills: List[dict]
    weak_skills: List[dict]
    ai_recommendation: Optional[str]
    job: "JobResponse"
    created_at: datetime
    matched_at: Optional[datetime] = None
    job_snapshot_available: bool = False

    @field_validator("matched_at")
    @classmethod
    def match_time_is_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @computed_field
    @property
    def skill_group_scores(self) -> Optional[List[SkillGroupScore]]:
        from app.services.skill_matcher import summarize_skill_groups

        groups = summarize_skill_groups(self.matched_skills, self.missing_skills, self.weak_skills)
        return [SkillGroupScore.model_validate(group) for group in groups] if groups is not None else None

    class Config:
        from_attributes = True


SkillGapResponse.model_rebuild()
