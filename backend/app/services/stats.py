"""Thong ke so tuyen: theo job (recruiter) va toan he thong (admin)."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cv import CV
from app.models.job import Job
from app.models.skill_gap import SkillGap
from app.models.user import User

REVIEW_STATUSES = ("new", "viewed", "shortlisted", "rejected", "hired")
SCORE_BUCKETS = ("0-24", "25-49", "50-74", "75-100")
# Gioi han so ban ghi khi quet JSON de tranh query khong gioi han.
MAX_GAPS_FOR_SKILL_STATS = 5000


def _score_bucket(score: float) -> str:
    if score >= 75:
        return "75-100"
    if score >= 50:
        return "50-74"
    if score >= 25:
        return "25-49"
    return "0-24"


def _top_skill_names(rows: list, key: str, limit: int = 10) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in rows:
        for item in row.get(key) or []:
            name = item.get("skill_name") if isinstance(item, dict) else None
            if name:
                counter[name] += 1
    return [{"skill_name": name, "count": count} for name, count in counter.most_common(limit)]


def job_stats(db: Session, job_id: int) -> dict[str, Any]:
    """Thong ke ung vien cho mot job: pipeline, phan bo diem, skill thieu/phu."""
    gaps = (
        db.query(SkillGap)
        .filter(SkillGap.job_id == job_id)
        .order_by(SkillGap.matched_at.desc(), SkillGap.id.desc())
        .all()
    )
    scores = [gap.match_score for gap in gaps if gap.match_score is not None]
    buckets = {bucket: 0 for bucket in SCORE_BUCKETS}
    for score in scores:
        buckets[_score_bucket(score)] += 1
    status_counts = {status: 0 for status in REVIEW_STATUSES}
    for gap in gaps:
        status_counts[gap.review_status or "new"] += 1
    payloads = [
        {"missing_skills": gap.missing_skills, "weak_skills": gap.weak_skills}
        for gap in gaps[:MAX_GAPS_FOR_SKILL_STATS]
    ]
    return {
        "job_id": job_id,
        "total_applicants": len(gaps),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "review_status_counts": status_counts,
        "score_buckets": buckets,
        "top_missing_skills": _top_skill_names(payloads, "missing_skills"),
        "top_weak_skills": _top_skill_names(payloads, "weak_skills"),
    }


def overview_stats(db: Session, days: int = 7) -> dict[str, Any]:
    """Thong ke van hanh toan he thong cho admin."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    role_rows = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    total_jobs = db.query(func.count(Job.id)).filter(Job.is_deleted.is_(False)).scalar() or 0
    active_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.is_deleted.is_(False), Job.is_active.is_(True))
        .scalar() or 0
    )
    total_cvs = db.query(func.count(CV.id)).scalar() or 0
    cv_status_rows = db.query(CV.status, func.count(CV.id)).group_by(CV.status).all()
    total_matches = db.query(func.count(SkillGap.id)).scalar() or 0
    review_rows = db.query(SkillGap.review_status, func.count(SkillGap.id)).group_by(SkillGap.review_status).all()
    new_users = db.query(func.count(User.id)).filter(User.created_at >= since).scalar() or 0
    new_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.is_deleted.is_(False), Job.created_at >= since)
        .scalar() or 0
    )
    new_cvs = db.query(func.count(CV.id)).filter(CV.created_at >= since).scalar() or 0
    new_matches = db.query(func.count(SkillGap.id)).filter(SkillGap.created_at >= since).scalar() or 0
    top_recruiters = (
        db.query(User.id, User.full_name, User.email, func.count(Job.id).label("job_count"))
        .join(Job, Job.owner_id == User.id)
        .filter(User.role == "recruiter", Job.is_deleted.is_(False))
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(Job.id).desc(), User.id.asc())
        .limit(5)
        .all()
    )
    recent_gaps = (
        db.query(SkillGap.missing_skills, SkillGap.weak_skills)
        .order_by(SkillGap.matched_at.desc(), SkillGap.id.desc())
        .limit(MAX_GAPS_FOR_SKILL_STATS)
        .all()
    )
    payloads = [
        {"missing_skills": missing, "weak_skills": weak} for missing, weak in recent_gaps
    ]
    return {
        "period_days": days,
        "totals": {
            "users": total_users,
            "active_users": active_users,
            "jobs": total_jobs,
            "active_jobs": active_jobs,
            "cvs": total_cvs,
            "matches": total_matches,
        },
        "new_in_period": {
            "users": new_users,
            "jobs": new_jobs,
            "cvs": new_cvs,
            "matches": new_matches,
        },
        "users_by_role": {role: count for role, count in role_rows},
        "cvs_by_status": {status: count for status, count in cv_status_rows},
        "matches_by_review_status": {
            (status or "new"): count for status, count in review_rows
        },
        "top_recruiters": [
            {"id": user_id, "full_name": name, "email": email, "job_count": count}
            for user_id, name, email, count in top_recruiters
        ],
        "top_missing_skills": _top_skill_names(payloads, "missing_skills"),
        "top_weak_skills": _top_skill_names(payloads, "weak_skills"),
    }


def recruiter_overview(db: Session, recruiter_id: int) -> dict[str, Any]:
    """Thong ke nhanh cho recruiter: job cua ho + tong ung vien + cho xu ly."""
    job_ids = [
        row[0] for row in
        db.query(Job.id).filter(Job.is_deleted.is_(False), Job.owner_id == recruiter_id).all()
    ]
    total_applicants = 0
    pending = 0
    per_job: list[dict[str, Any]] = []
    if job_ids:
        total_applicants = (
            db.query(func.count(SkillGap.id)).filter(SkillGap.job_id.in_(job_ids)).scalar() or 0
        )
        pending = (
            db.query(func.count(SkillGap.id))
            .filter(SkillGap.job_id.in_(job_ids), SkillGap.review_status == "new")
            .scalar() or 0
        )
        rows = (
            db.query(Job.id, Job.title, func.count(SkillGap.id))
            .outerjoin(SkillGap, SkillGap.job_id == Job.id)
            .filter(Job.id.in_(job_ids))
            .group_by(Job.id, Job.title)
            .order_by(Job.id.desc())
            .limit(5)
            .all()
        )
        per_job = [
            {"id": job_id, "title": title, "applicants": count}
            for job_id, title, count in rows
        ]
    return {
        "total_jobs": len(job_ids),
        "total_applicants": total_applicants,
        "pending_review": pending,
        "recent_jobs": per_job,
    }
