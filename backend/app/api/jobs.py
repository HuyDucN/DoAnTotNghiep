from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import csv
import io
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin, get_current_admin_or_recruiter
from app.models.job import Job, JobSkill
from app.models.skill import Skill, CVSkill
from app.models.cv import CV
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.job import (
    JobCreate, JobUpdate, JobResponse, SkillGapResponse, PaginatedResponse,
    JobDescriptionParseRequest, JobDescriptionParseResponse, AdminJobListResponse,
    ApplicantResponse, ApplicantReviewUpdate, JobStatsResponse, NewApplicantNotice,
)
from app.schemas.user import RecruiterOverviewResponse
from app.services.stats import job_stats as build_job_stats, recruiter_overview as build_recruiter_overview
from app.services.job_matching import match_with_current_data
from app.services.match_history import skill_gap_response
from app.services.ai_analyzer import generate_recommendation, parse_job_description_with_ai
from app.services.skill_names import normalize_skill_name
from app.services.skill_catalog import get_or_create_skill
from app.services.audit import log_audit
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
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Phân trang job chưa xóa. Recruiter chỉ thấy job của họ."""
    query = db.query(Job).filter(Job.is_deleted.is_(False))
    if current_user.role == "recruiter":
        query = query.filter(Job.owner_id == current_user.id)
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
    _: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Bóc tách JD thành dữ liệu Job có cấu trúc bằng AI."""
    return parse_job_description_with_ai(payload.description)


@router.post("/admin", response_model=JobResponse, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Tạo Job mới. Job do recruiter tạo thuộc sở hữu của họ."""
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
        owner_id=current_user.id,
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

    log_audit(db, current_user.id, "job.create", target_type="job", target_id=job.id,
              detail={"title": job.title})
    db.commit()
    db.refresh(job)
    return job


@router.put("/admin/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Cập nhật các trường được gửi; mỗi nhóm skill thay thế riêng."""
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    if current_user.role == "recruiter" and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ được sửa job do bạn đăng")

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

    log_audit(db, current_user.id, "job.update", target_type="job", target_id=job.id,
              detail={"fields": sorted(changes.keys())})
    db.commit()
    db.refresh(job)
    return job


@router.delete("/admin/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Xóa mềm Job (Soft Delete — không xóa thật, bảo toàn lịch sử so khớp CV)."""
    job = db.query(Job).filter(Job.id == job_id, Job.is_deleted == False).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    if current_user.role == "recruiter" and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ được xóa job do bạn đăng")
    # Soft delete: chỉ ẩn, không xóa dữ liệu — giữ nguyên lịch sử SkillGap
    job.is_deleted = True
    job.deleted_at = datetime.now(timezone.utc)
    job.is_active = False
    log_audit(db, current_user.id, "job.delete", target_type="job", target_id=job.id)
    db.commit()


def _require_job_owner(db: Session, job_id: int, current_user: User) -> Job:
    """Job phải tồn tại, chưa xóa; recruiter chỉ chạm job của họ."""
    job = db.query(Job).filter(Job.id == job_id, Job.is_deleted.is_(False)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    if current_user.role == "recruiter" and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ được xem ứng viên của job do bạn đăng")
    return job


@router.get("/admin/{job_id}/applicants", response_model=PaginatedResponse[ApplicantResponse])
def list_job_applicants(
    job_id: int,
    review_status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Ứng viên đã match job, mới nhất trước. Recruiter giới hạn job của họ."""
    _require_job_owner(db, job_id, current_user)
    query = (
        db.query(SkillGap)
        .join(User, User.id == SkillGap.user_id)
        .join(CV, CV.id == SkillGap.cv_id)
        .filter(SkillGap.job_id == job_id)
    )
    if review_status:
        if review_status not in ("new", "viewed", "shortlisted", "rejected", "hired"):
            raise HTTPException(status_code=422, detail="Trạng thái sơ tuyển không hợp lệ")
        query = query.filter(SkillGap.review_status == review_status)
    total = query.count()
    pages = max(1, -(-total // size))
    rows = (
        query.order_by(SkillGap.matched_at.desc(), SkillGap.created_at.desc(), SkillGap.id.desc())
        .offset((page - 1) * size).limit(size).all()
    )
    items = [
        ApplicantResponse(
            id=gap.id, user_id=gap.user_id,
            candidate_name=gap.user.full_name, candidate_email=gap.user.email,
            cv_id=gap.cv_id, cv_filename=gap.cv.filename,
            match_score=gap.match_score,
            matched_skills=gap.matched_skills or [],
            missing_skills=gap.missing_skills or [],
            weak_skills=gap.weak_skills or [],
            review_status=gap.review_status or "new",
            recruiter_note=gap.recruiter_note,
            reviewed_at=gap.reviewed_at,
            matched_at=gap.matched_at,
        )
        for gap in rows
    ]
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.patch("/admin/applicants/{gap_id}", response_model=ApplicantResponse)
def review_applicant(
    gap_id: int,
    payload: ApplicantReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Cập nhật trạng thái sơ tuyển / ghi chú nội bộ."""
    gap = db.query(SkillGap).filter(SkillGap.id == gap_id).with_for_update().first()
    if not gap:
        raise HTTPException(status_code=404, detail="Lượt ứng tuyển không tồn tại")
    _require_job_owner(db, gap.job_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "review_status" in changes:
        gap.review_status = changes["review_status"]
    if "recruiter_note" in changes:
        gap.recruiter_note = changes["recruiter_note"]
    gap.reviewed_at = datetime.now(timezone.utc)
    log_audit(db, current_user.id, "applicant.review", target_type="skill_gap", target_id=gap.id,
              detail={"job_id": gap.job_id, **{k: v for k, v in changes.items() if k != "recruiter_note"}})
    db.commit()
    db.refresh(gap)
    return ApplicantResponse(
        id=gap.id, user_id=gap.user_id,
        candidate_name=gap.user.full_name, candidate_email=gap.user.email,
        cv_id=gap.cv_id, cv_filename=gap.cv.filename,
        match_score=gap.match_score,
        matched_skills=gap.matched_skills or [],
        missing_skills=gap.missing_skills or [],
        weak_skills=gap.weak_skills or [],
        review_status=gap.review_status or "new",
        recruiter_note=gap.recruiter_note,
        reviewed_at=gap.reviewed_at,
        matched_at=gap.matched_at,
    )


@router.get("/admin/{job_id}/stats", response_model=JobStatsResponse)
def get_job_stats(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Thống kê sơ tuyển cho một job. Recruiter giới hạn job của họ."""
    _require_job_owner(db, job_id, current_user)
    return build_job_stats(db, job_id)


@router.get("/admin-overview/mine", response_model=RecruiterOverviewResponse)
def get_my_recruiter_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """Thống kê nhanh cho recruiter: job của họ, ứng viên, chờ xử lý."""
    return build_recruiter_overview(db, current_user.id)


@router.get("/admin/notifications/new-applicants", response_model=List[NewApplicantNotice])
def list_new_applicant_notices(
    days: int = Query(default=7, ge=1, le=30, description="Số ngày tính ứng viên mới"),
    limit: int = Query(default=20, ge=1, le=50, description="Số thông báo tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Ứng viên mới (trạng thái new) trong N ngày. Recruiter chỉ job của họ."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        db.query(SkillGap)
        .join(Job, Job.id == SkillGap.job_id)
        .filter(Job.is_deleted.is_(False), SkillGap.review_status == "new",
                SkillGap.matched_at >= since)
    )
    if current_user.role == "recruiter":
        query = query.filter(Job.owner_id == current_user.id)
    rows = (
        query.order_by(SkillGap.matched_at.desc(), SkillGap.id.desc())
        .limit(limit).all()
    )
    return [
        NewApplicantNotice(
            id=gap.id, user_id=gap.user_id,
            candidate_name=gap.user.full_name, candidate_email=gap.user.email,
            cv_id=gap.cv_id, cv_filename=gap.cv.filename,
            match_score=gap.match_score,
            matched_skills=gap.matched_skills or [],
            missing_skills=gap.missing_skills or [],
            weak_skills=gap.weak_skills or [],
            review_status=gap.review_status or "new",
            recruiter_note=gap.recruiter_note,
            reviewed_at=gap.reviewed_at,
            matched_at=gap.matched_at,
            job_id=gap.job_id, job_title=gap.job.title,
        )
        for gap in rows
    ]


@router.post("/admin/{job_id}/duplicate", response_model=JobResponse, status_code=201)
def duplicate_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Nhân bản job (kèm kỹ năng) thành tin mới. Recruiter chỉ job của họ."""
    source = db.query(Job).options(
        joinedload(Job.job_skills)
    ).filter(Job.id == job_id, Job.is_deleted.is_(False)).first()
    if not source:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    if current_user.role == "recruiter" and source.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ được nhân bản job do bạn đăng")
    clone = Job(
        title=f"{source.title} (bản sao)",
        company=source.company, location=source.location,
        job_type=source.job_type, level=source.level, category=source.category,
        description=source.description,
        salary_min=source.salary_min, salary_max=source.salary_max,
        owner_id=current_user.id, is_active=False,
    )
    db.add(clone)
    db.flush()
    for js in source.job_skills:
        db.add(JobSkill(job_id=clone.id, skill_id=js.skill_id,
                        is_required=js.is_required, importance=js.importance))
    log_audit(db, current_user.id, "job.duplicate", target_type="job", target_id=clone.id,
              detail={"source_job_id": source.id})
    db.commit()
    db.refresh(clone)
    return clone


def _applicant_row_csv(gap: SkillGap) -> List[str]:
    return [
        str(gap.id), gap.user.full_name, gap.user.email, gap.cv.filename,
        str(gap.match_score), gap.review_status or "new",
        gap.recruiter_note or "",
        gap.matched_at.isoformat() if gap.matched_at else "",
    ]


@router.get("/admin/{job_id}/applicants/export")
def export_job_applicants_csv(
    job_id: int,
    review_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_recruiter),
):
    """[Admin/Recruiter] Xuất CSV danh sách ứng viên của job (tối đa 2000 dòng)."""
    _require_job_owner(db, job_id, current_user)
    if review_status and review_status not in ("new", "viewed", "shortlisted", "rejected", "hired"):
        raise HTTPException(status_code=422, detail="Trạng thái sơ tuyển không hợp lệ")
    query = (
        db.query(SkillGap)
        .filter(SkillGap.job_id == job_id)
    )
    if review_status:
        query = query.filter(SkillGap.review_status == review_status)
    rows = (
        query.order_by(SkillGap.matched_at.desc(), SkillGap.id.desc())
        .limit(2000).all()
    )
    buffer = io.StringIO()
    buffer.write("﻿")
    writer = csv.writer(buffer)
    writer.writerow(["id", "candidate_name", "candidate_email", "cv_filename",
                     "match_score", "review_status", "recruiter_note", "matched_at"])
    for gap in rows:
        writer.writerow(_applicant_row_csv(gap))
    log_audit(db, current_user.id, "applicant.export", target_type="job", target_id=job_id,
              detail={"count": len(rows)})
    db.commit()
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=job-{job_id}-applicants.csv"},
    )
