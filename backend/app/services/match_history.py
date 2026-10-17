"""Dựng báo cáo từ thông tin công việc đã lưu tại thời điểm so khớp."""
import logging

from pydantic import ValidationError

from app.models.skill_gap import SkillGap
from app.schemas.job import JobResponse, SkillGapResponse
from app.services.cv_match_state import cv_match_status


logger = logging.getLogger(__name__)


def skill_gap_response(gap: SkillGap) -> SkillGapResponse:
    historical_job = None
    if gap.job_snapshot is not None:
        try:
            candidate = JobResponse.model_validate(gap.job_snapshot)
            if candidate.id == gap.job_id:
                historical_job = candidate
            else:
                logger.warning("Job snapshot ID mismatch for skill gap %s", gap.id)
        except ValidationError:
            logger.warning("Invalid job snapshot for skill gap %s", gap.id)
    return SkillGapResponse(
        id=gap.id,
        cv_id=gap.cv_id,
        cv_filename=gap.cv.filename,
        cv_match_status=cv_match_status(gap.cv, gap.cv_input_hash),
        match_score=gap.match_score,
        matched_skills=gap.matched_skills,
        missing_skills=gap.missing_skills,
        weak_skills=gap.weak_skills,
        ai_recommendation=gap.ai_recommendation,
        job=historical_job if historical_job is not None else JobResponse.model_validate(gap.job),
        created_at=gap.created_at,
        matched_at=gap.matched_at,
        job_snapshot_available=historical_job is not None,
    )
