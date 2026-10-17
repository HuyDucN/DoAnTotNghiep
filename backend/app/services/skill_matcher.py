"""
Skill Matching Engine
So khớp CV Skills với Job Skills → Match Score + Skill Gap analysis
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.cv import CV
from app.models.job import Job, JobSkill
from app.models.skill import CVSkill, Skill
from app.services.skill_names import normalize_skill_name


# Trọng số dùng trực tiếp từ JobSkill.importance. Required luôn nặng hơn
# Preferred, đồng thời mức high/medium/low tạo khác biệt trong cùng nhóm.
REQUIRED_WEIGHTS = {"high": 1.0, "medium": 0.8, "low": 0.6}
PREFERRED_WEIGHTS = {"high": 0.5, "medium": 0.3, "low": 0.2}


def _get_skill_weight(is_required: bool, importance: str) -> float:
    weights = REQUIRED_WEIGHTS if is_required else PREFERRED_WEIGHTS
    return weights.get(importance, weights["medium"])


def _weighted_percentage(matched_weight: float, total_weight: float) -> float:
    return round((matched_weight / total_weight) * 100, 1) if total_weight else 0.0


def summarize_skill_groups(matched_skills: list, missing_skills: list, weak_skills: list) -> list[dict] | None:
    """Tỷ lệ trọng số đạt theo importance, dùng các skill snapshot của kết quả.

    Dữ liệu cũ thiếu thông tin trọng số không đủ để dựng biểu đồ đáng tin cậy.
    Kỹ năng yếu và thiếu đều góp vào mẫu số, không góp vào phần đã đạt.
    """
    all_skills = matched_skills + missing_skills + weak_skills
    if any("importance" not in skill or "is_required" not in skill for skill in all_skills):
        return None
    groups = {
        importance: {"importance": importance, "matched_weight": 0.0, "total_weight": 0.0}
        for importance in ("high", "medium", "low")
    }
    for is_matched, skills in ((True, matched_skills), (False, missing_skills), (False, weak_skills)):
        for skill in skills:
            importance = skill["importance"] if skill["importance"] in ("high", "medium", "low") else "medium"
            weight = _get_skill_weight(skill["is_required"], importance)
            group = groups[importance]
            group["total_weight"] += weight
            if is_matched:
                group["matched_weight"] += weight
    return [
        {
            "importance": group["importance"],
            "matched_weight": round(group["matched_weight"], 4),
            "total_weight": round(group["total_weight"], 4),
            "score": _weighted_percentage(group["matched_weight"], group["total_weight"]),
        }
        for group in groups.values()
    ]


def calculate_match_score(cv: CV, job: Job, db: Session, *, cv_skills: List[CVSkill] | None = None) -> dict:
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
    # A caller holding row locks can supply those exact rows. An ordinary SELECT
    # in MySQL REPEATABLE READ may otherwise read an earlier transaction snapshot.
    if cv_skills is None:
        cv_skills = (
            db.query(CVSkill)
            .join(Skill)
            .filter(CVSkill.cv_id == cv.id)
            .all()
        )

    # Chuẩn hóa từ tên thật để khóa cũ (nodejs/c) không gây khớp sai.
    cv_skill_map = {}
    for cs in cv_skills:
        normalized = normalize_skill_name(cs.skill.name)
        source = getattr(cs, "source", None)
        previous = cv_skill_map.get(normalized)
        # Hai bản ghi cũ có thể mang cùng tên chuẩn hóa nhưng khác khóa lưu.
        # Giá trị người dùng sửa tay được ưu tiên bất kể thứ tự query trả về.
        if previous and previous["source"] == "manual" and source != "manual":
            continue
        cv_skill_map[normalized] = {
            "skill_id": cs.skill.id,
            "skill_name": cs.skill.name,
            "proficiency_level": cs.proficiency_level,
            "years_experience": cs.years_experience,
            "source": source,
        }

    # Separate required vs preferred job skills
    required_job_skills = [js for js in job.job_skills if js.is_required]
    preferred_job_skills = [js for js in job.job_skills if not js.is_required]

    PROFICIENCY_ORDER = ["beginner", "intermediate", "advanced", "expert"]
    minimum_by_job_level = {
        "intern": "beginner", "fresher": "beginner", "junior": "intermediate",
        "mid": "intermediate", "senior": "advanced", "lead": "advanced",
    }
    needed_level = minimum_by_job_level.get(job.level, "intermediate")

    matched_skills = []
    missing_skills = []
    weak_skills = []

    # --- Process required skills ---
    for js in required_job_skills:
        norm_name = normalize_skill_name(js.skill.name)
        cv_skill_data = cv_skill_map.get(norm_name)

        if cv_skill_data:
            cv_level = cv_skill_data["proficiency_level"]
            # Check if proficiency is sufficient (at least intermediate for required)
            if PROFICIENCY_ORDER.index(cv_level) >= PROFICIENCY_ORDER.index(needed_level):
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
                    "needed_level": needed_level,
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
        norm_name = normalize_skill_name(js.skill.name)
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
    # Formula: cộng trọng số riêng của từng JobSkill theo required + importance.
    total_weight = sum(
        _get_skill_weight(js.is_required, js.importance)
        for js in job.job_skills
    )
    if total_weight == 0:
        match_score = 0.0
    else:
        earned_weight = sum(
            _get_skill_weight(skill["is_required"], skill["importance"])
            for skill in matched_skills
        )
        match_score = _weighted_percentage(earned_weight, total_weight)

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
