from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.job import Job, JobSkill
from app.models.skill import Skill
from app.models.cv import CV
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate, JobResponse, SkillGapResponse
from app.services.skill_matcher import calculate_match_score
from app.services.ai_analyzer import generate_recommendation

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    category: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách tất cả job (có filter)."""
    query = db.query(Job).options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
    query = query.filter(Job.is_active == True)

    if category:
        query = query.filter(Job.category == category)
    if level:
        query = query.filter(Job.level == level)
    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))

    return query.order_by(Job.created_at.desc()).all()


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
        .filter(Job.id == job_id)
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
):
    """So sánh CV với Job → tính Match Score và Skill Gap."""
    # Validate CV belongs to user
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.status != "analyzed":
        raise HTTPException(status_code=400, detail="CV chưa được phân tích. Vui lòng chờ AI xử lý xong.")

    # Validate job exists
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    # Calculate match
    result = calculate_match_score(cv, job, db)

    # Generate AI recommendation
    ai_rec = generate_recommendation(
        cv_analysis=cv.ai_analysis,
        missing_skills=result["missing_skills"],
        job_title=job.title,
    )

    # Save or update skill gap record
    existing = db.query(SkillGap).filter(
        SkillGap.user_id == current_user.id,
        SkillGap.cv_id == cv_id,
        SkillGap.job_id == job_id,
    ).first()

    if existing:
        existing.match_score = result["match_score"]
        existing.matched_skills = result["matched_skills"]
        existing.missing_skills = result["missing_skills"]
        existing.weak_skills = result["weak_skills"]
        existing.ai_recommendation = ai_rec
        skill_gap = existing
    else:
        skill_gap = SkillGap(
            user_id=current_user.id,
            cv_id=cv_id,
            job_id=job_id,
            match_score=result["match_score"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            weak_skills=result["weak_skills"],
            ai_recommendation=ai_rec,
        )
        db.add(skill_gap)

    db.commit()
    db.refresh(skill_gap)
    return skill_gap


@router.get("/history/gaps", response_model=List[SkillGapResponse])
def get_my_skill_gaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lịch sử phân tích Skill Gap của user."""
    return (
        db.query(SkillGap)
        .options(joinedload(SkillGap.job))
        .filter(SkillGap.user_id == current_user.id)
        .order_by(SkillGap.created_at.desc())
        .all()
    )


# Admin routes
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
        normalized = skill_data.skill_name.lower().replace(" ", "_").replace("-", "_")
        skill = db.query(Skill).filter(Skill.normalized_name == normalized).first()
        if not skill:
            skill = Skill(name=skill_data.skill_name, normalized_name=normalized)
            db.add(skill)
            db.flush()

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
    """[Admin] Cập nhật Job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    for field in ["title", "company", "location", "job_type", "level", "category", "description", "salary_min", "salary_max"]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(job, field, val)

    db.commit()
    db.refresh(job)
    return job


@router.delete("/admin/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """[Admin] Xóa Job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    db.delete(job)
    db.commit()
