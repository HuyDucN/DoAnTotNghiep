import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.cv import CV
from app.schemas.cv import CVResponse
from app.services.cv_parser import extract_text_from_file
from app.services.ai_analyzer import analyze_cv_with_ai

router = APIRouter(prefix="/cv", tags=["CV Management"])

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}


@router.post("/upload", response_model=CVResponse, status_code=201)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload CV (PDF/DOCX) và trigger AI analysis."""
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF hoặc DOCX")

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File không được vượt quá {settings.MAX_FILE_SIZE_MB}MB")

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = ALLOWED_TYPES[file.content_type]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Create CV record
    cv = CV(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(contents),
        status="uploaded",
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    # Trigger background AI analysis
    background_tasks.add_task(process_cv_analysis, cv.id, file_path)

    return cv


@router.get("/list", response_model=List[CVResponse])
def list_cvs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách CV của user hiện tại."""
    return db.query(CV).filter(CV.user_id == current_user.id).order_by(CV.created_at.desc()).all()


@router.get("/{cv_id}", response_model=CVResponse)
def get_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chi tiết một CV."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    return cv


@router.delete("/{cv_id}", status_code=204)
def delete_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa CV."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")

    # Delete file from disk
    if os.path.exists(cv.file_path):
        os.remove(cv.file_path)

    db.delete(cv)
    db.commit()


@router.post("/{cv_id}/reanalyze", response_model=CVResponse)
def reanalyze_cv(
    cv_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phân tích lại CV bằng AI."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.status == "processing":
        raise HTTPException(status_code=400, detail="CV đang được phân tích")

    cv.status = "processing"
    db.commit()
    background_tasks.add_task(process_cv_analysis, cv.id, cv.file_path)
    return cv


def process_cv_analysis(cv_id: int, file_path: str):
    """Background task: extract text → AI analysis → save results."""
    from app.core.database import SessionLocal
    # Use a new DB session in background task
    session = SessionLocal()
    try:
        cv = session.query(CV).filter(CV.id == cv_id).first()
        if not cv:
            return

        cv.status = "processing"
        session.commit()

        # Step 1: Extract text
        raw_text = extract_text_from_file(file_path)
        if not raw_text or len(raw_text.strip()) < 50:
            cv.status = "failed"
            session.commit()
            return

        cv.raw_text = raw_text

        # Step 2: AI analysis
        analysis = analyze_cv_with_ai(raw_text)
        if analysis:
            cv.ai_analysis = analysis
            cv.status = "analyzed"
            # Save extracted skills to cv_skills table
            _save_cv_skills(cv_id, analysis.get("skills", []), session)
        else:
            cv.status = "failed"

        session.commit()
    except Exception as e:
        session.rollback()
        cv = session.query(CV).filter(CV.id == cv_id).first()
        if cv:
            cv.status = "failed"
            session.commit()
    finally:
        session.close()


def _save_cv_skills(cv_id: int, skills_data: list, session: Session):
    """Save normalized skills extracted by AI into cv_skills table."""
    from app.models.skill import Skill, CVSkill

    # Clear existing cv_skills
    session.query(CVSkill).filter(CVSkill.cv_id == cv_id).delete()

    for skill_data in skills_data:
        skill_name = skill_data.get("name", "").strip()
        if not skill_name:
            continue

        normalized = skill_name.lower().replace(" ", "_").replace("-", "_")

        # Find or create skill
        skill = session.query(Skill).filter(Skill.normalized_name == normalized).first()
        if not skill:
            skill = Skill(
                name=skill_name,
                normalized_name=normalized,
                category=skill_data.get("category", "other"),
            )
            session.add(skill)
            session.flush()

        # Create cv_skill link
        cv_skill = CVSkill(
            cv_id=cv_id,
            skill_id=skill.id,
            proficiency_level=skill_data.get("proficiency_level", "intermediate"),
            years_experience=float(skill_data.get("years_experience", 0)),
        )
        session.add(cv_skill)
