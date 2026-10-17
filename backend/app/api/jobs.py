from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.job import Job, JobSkill
from app.models.skill import Skill, CVSkill
from app.models.cv import CV
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.job import (
    JobCreate, JobUpdate, JobResponse, SkillGapResponse, PaginatedResponse,
    JobDescriptionParseRequest, JobDescriptionParseResponse, AdminJobListResponse,
)
from app.services.job_matching import match_with_current_data
from app.services.match_history import skill_gap_response
from app.services.ai_analyzer import generate_recommendation, parse_job_description_with_ai
from app.services.skill_names import normalize_skill_name
from app.services.skill_catalog import get_or_create_skill
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _repair_mojibake(value: Optional[str]) -> Optional[str]:
    """Khôi phục chuỗi tiếng Việt bị đọc nhầm UTF-8 thành Latin-1."""
    if not value or not any(marker in value for marker in ("Ã", "Â", "Ä", "á»", "Báº")):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _get_or_restore_skill(db: Session, normalized: str, display_name: str) -> Skill:
    """Lấy Skill hiện có hoặc khôi phục bản ghi đã xóa mềm.

    normalized_name là UNIQUE nên không thể tạo một dòng mới có cùng tên sau
    khi xóa mềm. Khôi phục dòng cũ cũng bảo toàn các liên kết lịch sử.
    """
    return get_or_create_skill(db, display_name)


def _filter_jobs(query, category=None, level=None, search=None):
    """Dùng chung bộ lọc cho danh sách ứng viên và danh sách quản trị."""
    if category:
        query = query.filter(Job.category == category)
    if level:
        query = query.filter(Job.level == level)
    keyword = (search or "").strip()
    if keyword:
        # Tìm theo đúng văn bản nhập, kể cả ký tự %, _ và dấu escape.
        escaped = keyword.replace("/", "//").replace("%", "/%").replace("_", "/_")
        pattern = f"%{escaped}%"
        query = query.filter(or_(
            Job.title.ilike(pattern, escape="/"),
            Job.company.ilike(pattern, escape="/"),
        ))
    return query


@router.get("/", response_model=PaginatedResponse[JobResponse])
def list_jobs(
    category: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    size: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang (tối đa 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách job đang tuyển dành cho ứng viên."""
    query = db.query(Job).options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
    query = query.filter(Job.is_active == True, Job.is_deleted == False)
    query = _filter_jobs(query, category=category, level=level, search=search)

    total = query.count()
    pages = max(1, -(-total // size))  # ceiling division
    items = query.order_by(Job.created_at.desc(), Job.id.desc()).offset((page - 1) * size).limit(size).all()

    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/admin/list", response_model=AdminJobListResponse)
def list_admin_jobs(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """[Admin] Phân trang job chưa xóa, bao gồm cả job ngừng hoạt động."""
    query = db.query(Job).filter(Job.is_deleted.is_(False))
    query = _filter_jobs(query, category=category, search=search)
    total = query.count()
    active_total = query.filter(Job.is_active.is_(True)).count()
    category_count = query.with_entities(func.count(func.distinct(Job.category))).scalar()
    pages = max(1, -(-total // size))
    # Trang cuối có thể mất sau khi xóa job; trả về trang cuối còn hợp lệ.
    page = min(page, pages)
    items = (
        query.options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .order_by(Job.created_at.desc(), Job.id.desc())
        .offset((page - 1) * size).limit(size).all()
    )
    return AdminJobListResponse(
        items=items, total=total, page=page, size=size, pages=pages,
        active_total=active_total, category_count=category_count,
    )


# Keep this static path before /{job_id}; otherwise "history" is parsed as an
# integer path parameter and the user's skill-gap history endpoint is hidden.
@router.get("/history/gaps", response_model=List[SkillGapResponse])
def get_my_skill_gaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gaps = (
        db.query(SkillGap)
        .options(joinedload(SkillGap.job), joinedload(SkillGap.cv).joinedload(CV.cv_skills).joinedload(CVSkill.skill))
        .filter(SkillGap.user_id == current_user.id)
        .order_by(SkillGap.matched_at.desc(), SkillGap.created_at.desc(), SkillGap.id.desc())
        .all()
    )
    responses = [skill_gap_response(gap) for gap in gaps]
    for response in responses:
        response.ai_recommendation = _repair_mojibake(response.ai_recommendation)
    return responses


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chi tiết một Job."""
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id, Job.is_active.is_(True), Job.is_deleted.is_(False))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    return job


@router.post("/{job_id}/match/{cv_id}", response_model=SkillGapResponse)
def match_cv_with_job(
    job_id: int,
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(20, 60)),
):
    """So sánh CV với Job → tính Match Score và Skill Gap."""
    return match_with_current_data(db, current_user.id, cv_id, job_id, generate_recommendation)


# Admin routes
@router.post("/admin/parse-description", response_model=JobDescriptionParseResponse)
def parse_job_description(
    payload: JobDescriptionParseRequest,
    _: User = Depends(get_current_admin),
):
    """[Admin] Bóc tách JD thành dữ liệu Job có cấu trúc bằng AI."""
    return parse_job_description_with_ai(payload.description)


@router.post("/admin", response_model=JobResponse, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """[Admin] Tạo Job mới."""
    job = Job(
        title=payload.title,
        company=payload.company,
        location=payload.location,
        job_type=payload.job_type,
        level=payload.level,
        category=payload.category,
        description=payload.description,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
    )
    db.add(job)
    db.flush()

    # Add skills
    all_skills = [
        (s, True) for s in payload.required_skills
    ] + [(s, False) for s in payload.preferred_skills]

    for skill_data, is_required in all_skills:
        normalized = normalize_skill_name(skill_data.skill_name)
        skill = _get_or_restore_skill(db, normalized, skill_data.skill_name)

        job_skill = JobSkill(
            job_id=job.id,
            skill_id=skill.id,
            is_required=is_required,
            importance=skill_data.importance,
        )
        db.add(job_skill)

    db.commit()
    db.refresh(job)
    return job


@router.put("/admin/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """[Admin] Cập nhật các trường được gửi; mỗi nhóm skill thay thế riêng."""
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    changes = payload.model_dump(exclude_unset=True, exclude={"required_skills", "preferred_skills"})
    for field, value in changes.items():
        setattr(job, field, value)

    for field, is_required in (("required_skills", True), ("preferred_skills", False)):
        if field not in payload.model_fields_set:
            continue
        db.query(JobSkill).filter(
            JobSkill.job_id == job.id,
            JobSkill.is_required.is_(is_required),
        ).delete(synchronize_session="fetch")
        for skill_data in getattr(payload, field):
            normalized = normalize_skill_name(skill_data.skill_name)
            skill = _get_or_restore_skill(db, normalized, skill_data.skill_name)
            db.add(JobSkill(job_id=job.id, skill_id=skill.id,
                            is_required=is_required, importance=skill_data.importance))

    db.commit()
    db.refresh(job)
    return job


@router.delete("/admin/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """[Admin] Xóa mềm Job (Soft Delete — không xóa thật, bảo toàn lịch sử so khớp CV)."""
    job = db.query(Job).filter(Job.id == job_id, Job.is_deleted == False).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    # Soft delete: chỉ ẩn, không xóa dữ liệu — giữ nguyên lịch sử SkillGap
    job.is_deleted = True
    job.deleted_at = datetime.now(timezone.utc)
    job.is_active = False
    db.commit()
