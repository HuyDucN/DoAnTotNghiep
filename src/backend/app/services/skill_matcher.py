"""
Skill Matching Engine
So khớp CV Skills với Job Skills → Match Score + Skill Gap analysis
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill


def calculate_match_score(cv: CV, job: Job, db: Session) -> dict:
    """
    So khớp kỹ năng CV với Job.
    
    Returns:
        {
            "match_score": float (0-100),
            "matched_skills": List[dict],
            "missing_skills": List[dict],
            "weak_skills": List[dict],
        }
    """
    # Load CV skills
    cv_skills: List[CVSkill] = (
        db.query(CVSkill)
        .join(Skill)
        .filter(CVSkill.cv_id == cv.id)
        .all()
    )

    # Build CV skill map: normalized_name → {level, years}
    cv_skill_map = {}
    for cs in cv_skills:
        cv_skill_map[cs.skill.normalized_name] = {
            "skill_id": cs.skill.id,
            "skill_name": cs.skill.name,
            "proficiency_level": cs.proficiency_level,
            "years_experience": cs.years_experience,
        }

    # Separate required vs preferred job skills
    required_job_skills = [js for js in job.job_skills if js.is_required]
    preferred_job_skills = [js for js in job.job_skills if not js.is_required]

    PROFICIENCY_ORDER = ["beginner", "intermediate", "advanced", "expert"]

    matched_skills = []
    missing_skills = []
    weak_skills = []

    # --- Process required skills ---
    for js in required_job_skills:
        norm_name = js.skill.normalized_name
        cv_skill_data = cv_skill_map.get(norm_name)

        if cv_skill_data:
            cv_level = cv_skill_data["proficiency_level"]
            # Check if proficiency is sufficient (at least intermediate for required)
            if PROFICIENCY_ORDER.index(cv_level) >= PROFICIENCY_ORDER.index("intermediate"):
                matched_skills.append({
                    "skill_id": js.skill_id,
                    "skill_name": js.skill.name,
                    "is_required": True,
                    "importance": js.importance,
                    "cv_level": cv_level,
                    "years_experience": cv_skill_data["years_experience"],
                })
            else:
                # Skill exists but level too low
                weak_skills.append({
                    "skill_id": js.skill_id,
                    "skill_name": js.skill.name,
                    "is_required": True,
                    "importance": js.importance,
                    "current_level": cv_level,
                    "needed_level": "intermediate",
                    "priority": _get_priority(js.importance, is_required=True),
                })
        else:
            missing_skills.append({
                "skill_id": js.skill_id,
                "skill_name": js.skill.name,
                "is_required": True,
                "importance": js.importance,
                "priority": _get_priority(js.importance, is_required=True),
            })

    # --- Process preferred skills ---
    for js in preferred_job_skills:
        norm_name = js.skill.normalized_name
        cv_skill_data = cv_skill_map.get(norm_name)

        if cv_skill_data:
            matched_skills.append({
                "skill_id": js.skill_id,
                "skill_name": js.skill.name,
                "is_required": False,
                "importance": js.importance,
                "cv_level": cv_skill_data["proficiency_level"],
                "years_experience": cv_skill_data["years_experience"],
            })
        else:
            missing_skills.append({
                "skill_id": js.skill_id,
                "skill_name": js.skill.name,
                "is_required": False,
                "importance": js.importance,
                "priority": _get_priority(js.importance, is_required=False),
            })

    # --- Calculate Match Score ---
    # Formula: weighted score
    # Required skills weight = 1.0 each, Preferred skills weight = 0.3 each
    total_weight = len(required_job_skills) * 1.0 + len(preferred_job_skills) * 0.3
    if total_weight == 0:
        match_score = 0.0
    else:
        matched_required = len([s for s in matched_skills if s["is_required"]])
        matched_preferred = len([s for s in matched_skills if not s["is_required"]])
        earned_weight = matched_required * 1.0 + matched_preferred * 0.3
        match_score = round((earned_weight / total_weight) * 100, 1)

    # Sort missing skills by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    missing_skills.sort(key=lambda x: priority_order.get(x["priority"], 99))
    weak_skills.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "weak_skills": weak_skills,
    }


def _get_priority(importance: str, is_required: bool) -> str:
    if is_required:
        if importance == "high":
            return "high"
        elif importance == "medium":
            return "high"  # Required medium = high priority to learn
        else:
            return "medium"
    else:
        if importance == "high":
            return "medium"
        else:
            return "low"
