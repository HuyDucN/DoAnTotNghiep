"""Đối chiếu dữ liệu CV hiện tại với đầu vào của lần so khớp đã lưu."""
from copy import deepcopy
import hashlib
import json
import re
from typing import Iterable, Literal

from app.models.cv import CV
from app.models.skill import CVSkill


CvMatchStatus = Literal["current", "changed", "processing", "failed", "unknown"]


def cv_match_signature(cv: CV, skills: Iterable[CVSkill]) -> dict:
    return {
        "cv": {
            "analysis_run_id": cv.analysis_run_id,
            "file_hash": cv.file_hash,
            "ai_analysis": deepcopy(cv.ai_analysis),
        },
        "cv_skills": [
            (row.id, row.skill_id, row.skill.name, row.proficiency_level, row.years_experience, row.source)
            for row in sorted(skills, key=lambda row: row.id)
        ],
    }


def cv_input_fingerprint(signature: dict) -> str:
    payload = {"format": 1, "cv": signature["cv"], "cv_skills": signature["cv_skills"]}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cv_match_status(cv: CV, stored_fingerprint: str | None) -> CvMatchStatus:
    if cv.status in {"uploaded", "processing"}:
        return "processing"
    if cv.status == "failed":
        return "failed"
    if cv.status != "analyzed" or not re.fullmatch(r"[0-9a-f]{64}", stored_fingerprint or ""):
        return "unknown"
    current = cv_input_fingerprint(cv_match_signature(cv, cv.cv_skills))
    return "current" if current == stored_fingerprint else "changed"
