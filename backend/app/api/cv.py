import os
import uuid
import shutil
import hashlib
from threading import Lock
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import Annotated, List
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.models.cv import CV
from app.models.skill import CVSkill
from app.schemas.cv import CVResponse, CVStatusResponse, CVSkillItemResponse, CVSkillManualRequest
from app.services.cv_parser import extract_text_from_file
from app.services.ai_analyzer import analyze_cv_with_ai
from app.services.skill_names import normalize_skill_name
from app.services.skill_catalog import get_or_create_skill
from app.services.cv_contacts import extract_cv_contacts
from app.services.upload_validation import validate_cv_upload
from app.services.cv_deletion import delete_stored_cv
from app.services.cv_upload import persist_cv_upload

router = APIRouter(prefix="/cv", tags=["CV Management"])

# BackgroundTasks chạy trong cùng tiến trình backend. Khóa theo hash ngăn hai
# task cùng lúc gọi AI cho đúng một nội dung file; task thứ hai sẽ thấy cache
# sau khi task thứ nhất hoàn tất. Khi chạy nhiều worker/server, Redis lock là
# bước mở rộng phù hợp hơn.
_analysis_locks: dict[str, Lock] = {}
_analysis_locks_guard = Lock()


def _get_analysis_lock(file_hash: str) -> Lock:
    with _analysis_locks_guard:
        return _analysis_locks.setdefault(file_hash, Lock())

@router.post("/upload", response_model=CVResponse, status_code=201)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(5, 60)),
):
    """Upload CV (PDF/DOCX) và trigger AI analysis."""
    # Validate file size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    contents = await file.read(max_size + 1)
    ext = validate_cv_upload(file.filename, file.content_type, contents, max_size)

    # Compute SHA-256 hash of file content (dùng cho cache AI)
    file_hash = hashlib.sha256(contents).hexdigest()

    result, file_path, run_id = persist_cv_upload(
        contents=contents,
        filename=file.filename or f"CV{ext}",
        extension=ext,
        file_hash=file_hash,
        user_id=current_user.id,
        db=db,
    )
    background_tasks.add_task(process_cv_analysis, result.id, file_path, run_id)
    return result


@router.get("/list", response_model=List[CVResponse])
def list_cvs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách CV của user hiện tại."""
    return db.query(CV).filter(CV.user_id == current_user.id).order_by(CV.created_at.desc()).all()


@router.get("/{cv_id}/status", response_model=CVStatusResponse)
def get_cv_status(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy trạng thái xử lý CV để frontend polling mà không tải JSON AI lớn."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    return cv


def _normalize_skill_name(name: str) -> str:
    return normalize_skill_name(name)


def _cv_skill_response(cv_skill: CVSkill) -> dict:
    return {
        "id": cv_skill.id,
        "skill_id": cv_skill.skill_id,
        "skill_name": cv_skill.skill.name,
        "proficiency_level": cv_skill.proficiency_level,
        "years_experience": cv_skill.years_experience or 0,
        "source": cv_skill.source or "ai_extracted",
    }


@router.get("/{cv_id}/skills", response_model=List[CVSkillItemResponse])
def list_cv_skills(
    cv_id: Annotated[int, Path(ge=1)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách kỹ năng của CV, bao gồm nguồn AI hoặc manual."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    rows = (
        db.query(CVSkill)
        .options(joinedload(CVSkill.skill))
        .filter(CVSkill.cv_id == cv_id)
        .all()
    )
    return [_cv_skill_response(row) for row in rows]


@router.post("/{cv_id}/skills", response_model=CVSkillItemResponse, status_code=201)
def upsert_manual_cv_skill(
    cv_id: Annotated[int, Path(ge=1)],
    payload: CVSkillManualRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thêm/cập nhật kỹ năng thủ công và luôn giữ source=manual."""
    skill_name = payload.skill_name.strip()
    normalized = _normalize_skill_name(skill_name)
    if not skill_name or not normalized:
        raise HTTPException(status_code=422, detail="Tên kỹ năng không hợp lệ")

    try:
        # Khóa CV khi ghi để hai request cùng CV không tạo trùng liên kết.
        cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).with_for_update().first()
        if not cv:
            raise HTTPException(status_code=404, detail="CV không tồn tại")
        if cv.status in {"uploaded", "processing"}:
            raise HTTPException(status_code=409, detail="CV đang được phân tích. Vui lòng chờ hoàn tất rồi sửa kỹ năng.")
        skill = get_or_create_skill(db, skill_name)

        cv_skill = db.query(CVSkill).filter(
            CVSkill.cv_id == cv_id,
            CVSkill.skill_id == skill.id,
        ).first()
        if not cv_skill:
            cv_skill = CVSkill(cv_id=cv_id, skill_id=skill.id)
            db.add(cv_skill)

        cv_skill.proficiency_level = payload.proficiency_level
        cv_skill.years_experience = payload.years_experience
        cv_skill.source = "manual"
        db.commit()
        db.refresh(cv_skill)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Kỹ năng đã tồn tại hoặc dữ liệu đang được cập nhật. Vui lòng tải lại và thử lại.",
        ) from exc
    return _cv_skill_response(cv_skill)


@router.delete("/{cv_id}/skills/{skill_id}", status_code=204)
def delete_manual_cv_skill(
    cv_id: Annotated[int, Path(ge=1)],
    skill_id: Annotated[int, Path(ge=1)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa liên kết kỹ năng khỏi CV mà không xóa Skill chuẩn hóa."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).with_for_update().first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.status in {"uploaded", "processing"}:
        raise HTTPException(status_code=409, detail="CV đang được phân tích. Vui lòng chờ hoàn tất rồi sửa kỹ năng.")
    cv_skill = db.query(CVSkill).filter(CVSkill.cv_id == cv_id, CVSkill.skill_id == skill_id).first()
    if not cv_skill:
        raise HTTPException(status_code=404, detail="Kỹ năng không tồn tại trong CV")
    try:
        db.delete(cv_skill)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dữ liệu kỹ năng đang được cập nhật. Vui lòng tải lại và thử lại.") from exc


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


@router.get("/{cv_id}/file")
def view_cv_file(cv_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Serve the original CV only to its owner."""
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv or not os.path.exists(cv.file_path):
        raise HTTPException(status_code=404, detail="File CV không tồn tại")
    media_type = "application/pdf" if cv.file_path.lower().endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(cv.file_path, media_type=media_type, filename=cv.filename)


@router.delete("/{cv_id}", status_code=204)
def delete_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa CV."""
    delete_stored_cv(cv_id, db, owner_id=current_user.id)


@router.post("/{cv_id}/reanalyze", response_model=CVResponse)
def reanalyze_cv(
    cv_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Phân tích lại CV bằng AI."""
    cv = (
        db.query(CV)
        .filter(CV.id == cv_id, CV.user_id == current_user.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    if cv.status in {"uploaded", "processing"}:
        last_update = cv.updated_at or cv.created_at
        if last_update and last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        if not last_update or datetime.now(timezone.utc) - last_update < timedelta(minutes=30):
            raise HTTPException(status_code=409, detail="CV đang chờ hoặc đang được phân tích. Vui lòng chờ hoàn tất.")

    run_id = uuid.uuid4().hex
    changed = (
        db.query(CV)
        .filter(CV.id == cv_id, CV.user_id == current_user.id, CV.status == cv.status, CV.analysis_run_id == cv.analysis_run_id)
        .update({
            CV.status: "uploaded",
            CV.analysis_run_id: run_id,
            CV.updated_at: datetime.now(timezone.utc).replace(tzinfo=None),
        }, synchronize_session=False)
    )
    if changed != 1:
        raise HTTPException(status_code=409, detail="CV vừa được cập nhật. Vui lòng tải lại và thử lại.")
    db.refresh(cv)
    result = CVResponse.model_validate(cv)
    file_path = cv.file_path
    db.commit()
    background_tasks.add_task(process_cv_analysis, cv_id, file_path, run_id)
    return result


def process_cv_analysis(cv_id: int, file_path: str, run_id: str | None = None):
    """Background task: extract text → AI analysis → save results.

    Tối ưu hóa: Kiểm tra cache theo SHA-256 hash — nếu có CV khác cùng hash đã được
    phân tích thành công, sao chép kết quả AI thay vì gọi lại OpenAI API.
    """
    from app.core.database import SessionLocal
    # Use a new DB session in background task
    session = SessionLocal()
    hash_lock = None
    claimed = False
    try:
        cv = session.query(CV).filter(CV.id == cv_id).first()
        if not cv:
            return
        if cv.status != "uploaded" or cv.analysis_run_id != run_id:
            return
        file_hash = cv.file_hash
        # End the read transaction before waiting for another analysis or doing I/O.
        session.rollback()
        if file_hash:
            lock = _get_analysis_lock(file_hash)
            lock.acquire()
            hash_lock = lock

        cv = _get_cv_for_analysis_update(session, cv_id)
        if cv is None or cv.status != "uploaded" or cv.analysis_run_id != run_id:
            return
        expected_run_id = run_id
        if run_id is None:
            # Initialize legacy queued rows when no attempt ID was supplied.
            run_id = uuid.uuid4().hex
        file_hash = cv.file_hash
        file_path = cv.file_path
        changed = (
            session.query(CV)
            .filter(CV.id == cv_id, CV.status == "uploaded", CV.analysis_run_id == expected_run_id)
            .update({
                CV.status: "processing", CV.analysis_run_id: run_id,
                CV.updated_at: datetime.now(timezone.utc).replace(tzinfo=None),
            }, synchronize_session=False)
        )
        if changed != 1:
            session.rollback()
            return
        session.commit()
        claimed = True

        # ── Cache check: tìm CV khác cùng hash đã analyzed ─────────────────────
        if file_hash:
            cached_cv = (
                session.query(CV)
                .filter(
                    CV.file_hash == file_hash,
                    CV.status == "analyzed",
                    CV.id != cv_id,
                    CV.ai_analysis.isnot(None),
                )
                .first()
            )
            if cached_cv:
                raw_text = cached_cv.raw_text
                analysis = {
                    **cached_cv.ai_analysis,
                    **extract_cv_contacts(raw_text or ""),
                }
                session.rollback()
                cv = _get_cv_for_analysis_update(session, cv_id)
                if not _analysis_run_is_current(cv, run_id):
                    return
                cv.raw_text = raw_text
                cv.ai_analysis = analysis
                cv.status = "analyzed"
                _save_cv_skills(cv_id, analysis.get("skills", []), session)
                session.commit()
                return
        session.rollback()

        # ── Step 1: Extract text ──────────────────────────────────────────────
        raw_text = extract_text_from_file(file_path)
        # Some valid CVs (especially DOCX files made from tables) contain very
        # little extractable text. Do not mark the upload failed just because
        # it is shorter than an arbitrary threshold; the analyzer can still
        # provide a development fallback or a useful API error.
        if not raw_text or not raw_text.strip():
            # Keep the record usable for the mock analyzer (and report a
            # meaningful analysis result instead of silently failing).
            raw_text = "CV không có lớp văn bản có thể trích xuất."

        # Do not submit extracted text to AI if deletion already completed.
        exists = session.query(CV.id).filter(
            CV.id == cv_id, CV.analysis_run_id == run_id, CV.status == "processing",
        ).first() is not None
        session.rollback()
        if not exists:
            return

        # ── Step 2: AI analysis ───────────────────────────────────────────────
        analysis = analyze_cv_with_ai(raw_text, file_path)
        cv = _get_cv_for_analysis_update(session, cv_id)
        if not _analysis_run_is_current(cv, run_id):
            return
        cv.raw_text = raw_text
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
        if not claimed:
            raise
        cv = _get_cv_for_analysis_update(session, cv_id)
        if _analysis_run_is_current(cv, run_id):
            print(f"[CV Analysis] CV {cv_id} failed: {e}")
            cv.status = "failed"
            session.commit()
    finally:
        if hash_lock is not None:
            hash_lock.release()
        session.close()


def _analysis_run_is_current(cv: CV | None, run_id: str) -> bool:
    return cv is not None and cv.analysis_run_id == run_id and cv.status == "processing"


def _get_cv_for_analysis_update(session: Session, cv_id: int):
    """Coordinate publication with deletion without locking during parser/AI I/O."""
    return (
        session.query(CV)
        .filter(CV.id == cv_id)
        .with_for_update()
        .populate_existing()
        .first()
    )


def _save_cv_skills(cv_id: int, skills_data: list, session: Session):
    """Lưu skill AI nhưng bảo toàn các skill người dùng đã xác nhận thủ công.

    Mỗi lần phân tích lại phải thay thế kết quả AI cũ. Liên kết có
    ``source=manual`` là dữ liệu người dùng xác nhận nên không được xóa hoặc
    ghi đè bởi kết quả AI mới.
    """
    existing_links = session.query(CVSkill).filter(CVSkill.cv_id == cv_id).all()
    manual_skill_ids = set()
    for link in existing_links:
        if link.source == "manual":
            manual_skill_ids.add(link.skill_id)
        else:
            # Null/legacy source được xem là kết quả AI cũ và có thể thay thế.
            session.delete(link)
    session.flush()

    saved_skill_ids = set()
    for skill_data in skills_data:
        skill_name = skill_data.get("name", "").strip()
        if not skill_name:
            continue

        skill = get_or_create_skill(session, skill_name, category=skill_data.get("category", "other"))

        # Manual skill wins over AI output for the same normalized skill.
        if skill.id in manual_skill_ids or skill.id in saved_skill_ids:
            continue

        # Create cv_skill link
        cv_skill = CVSkill(
            cv_id=cv_id,
            skill_id=skill.id,
            proficiency_level=skill_data.get("proficiency_level", "intermediate"),
            years_experience=float(skill_data.get("years_experience", 0)),
            source="ai_extracted",
        )
        session.add(cv_skill)
        saved_skill_ids.add(skill.id)
