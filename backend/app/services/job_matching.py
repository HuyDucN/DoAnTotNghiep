"""So khớp bằng dữ liệu đã chốt; xác nhận lại trước khi lưu lời khuyên AI."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.schemas.job import JobResponse, SkillGapResponse
from app.services.skill_matcher import calculate_match_score
from app.services.match_history import skill_gap_response
from app.services.cv_match_state import cv_match_signature, cv_input_fingerprint


@dataclass
class MatchSnapshot:
    signature: dict
    result: dict
    cv_analysis: dict | None
    job_title: str


def _load_match_snapshot(db: Session, user_id: int, cv_id: int, job_id: int, *, rechecking: bool = False) -> MatchSnapshot:
    # Use the same parent locks as account, CV and job writers. No locks survive AI I/O.
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không còn hoạt động", headers={"WWW-Authenticate": "Bearer"})
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == user_id).with_for_update().populate_existing().first()
    if cv is None:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.status != "analyzed":
        raise HTTPException(
            status_code=409 if rechecking else 400,
            detail="CV đã thay đổi. Vui lòng chờ phân tích hoàn tất rồi so khớp lại." if rechecking
            else "CV chưa được phân tích. Vui lòng chờ AI xử lý xong.",
        )
    job = db.query(Job).filter(
        Job.id == job_id, Job.is_active.is_(True), Job.is_deleted.is_(False),
    ).with_for_update().populate_existing().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job không tồn tại hoặc đã ngừng tuyển")

    cv_skills = db.query(CVSkill).filter(CVSkill.cv_id == cv_id).order_by(CVSkill.id).with_for_update().populate_existing().all()
    job_skills = db.query(JobSkill).filter(JobSkill.job_id == job_id).order_by(JobSkill.id).with_for_update().populate_existing().all()
    skill_ids = sorted({row.skill_id for row in cv_skills + job_skills})
    skills = db.query(Skill).filter(Skill.id.in_(skill_ids)).order_by(Skill.id).with_for_update().populate_existing().all() if skill_ids else []
    by_id = {skill.id: skill for skill in skills}
    for row in cv_skills + job_skills:
        if row.skill_id not in by_id:
            raise HTTPException(status_code=409, detail="Dữ liệu kỹ năng chưa đồng bộ. Vui lòng tải lại và thử lại.")
        set_committed_value(row, "skill", by_id[row.skill_id])
    # Populate relationships without marking any database row as changed.
    set_committed_value(job, "job_skills", job_skills)
    set_committed_value(cv, "cv_skills", cv_skills)
    result = calculate_match_score(cv, job, db, cv_skills=cv_skills)
    signature = {
        **cv_match_signature(cv, cv_skills),
        "job": JobResponse.model_validate(job).model_dump(mode="json"),
        "job_skill_ids": [row.id for row in job_skills],
    }
    return MatchSnapshot(signature, result, deepcopy(cv.ai_analysis), job.title)


def match_with_current_data(
    db: Session,
    user_id: int,
    cv_id: int,
    job_id: int,
    recommend: Callable[..., str],
) -> SkillGapResponse:
    db.rollback()
    initial = _load_match_snapshot(db, user_id, cv_id, job_id)
    db.rollback()
    recommendation = recommend(
        cv_analysis=deepcopy(initial.cv_analysis),
        missing_skills=deepcopy(initial.result["missing_skills"]),
        weak_skills=deepcopy(initial.result["weak_skills"]),
        job_title=initial.job_title,
    )
    current = _load_match_snapshot(db, user_id, cv_id, job_id, rechecking=True)
    if current.signature != initial.signature:
        raise HTTPException(status_code=409, detail="CV hoặc yêu cầu công việc đã thay đổi. Vui lòng so khớp lại.")

    gap = db.query(SkillGap).filter(
        SkillGap.user_id == user_id, SkillGap.cv_id == cv_id, SkillGap.job_id == job_id,
    ).with_for_update().populate_existing().first()
    if gap is None:
        gap = SkillGap(user_id=user_id, cv_id=cv_id, job_id=job_id)
        db.add(gap)
    for field, value in initial.result.items():
        setattr(gap, field, value)
    gap.ai_recommendation = recommendation
    gap.job_snapshot = deepcopy(current.signature["job"])
    gap.cv_input_hash = cv_input_fingerprint(current.signature)
    gap.matched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.flush()
        response = skill_gap_response(gap)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Kết quả so khớp vừa được cập nhật. Vui lòng thử lại.") from error
    return response
