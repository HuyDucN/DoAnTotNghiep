"""Lưu file và bản ghi CV, dọn file khi xác nhận giao dịch chưa thành công."""
import logging
from pathlib import Path
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cv import CV
from app.schemas.cv import CVResponse


logger = logging.getLogger(__name__)


def _stored_cv_id(db: Session, cv_id: int, file_path: str) -> int | None:
    # A fresh session avoids reusing the failed transaction or an ORM identity map.
    with Session(bind=db.get_bind()) as verification:
        return verification.query(CV.id).filter(
            CV.id == cv_id, CV.file_path == file_path,
        ).scalar()


def _rollback_upload(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        # A commit can succeed before a connection error or an after_commit error.
        # SQLAlchemy may then refuse rollback until the session is closed.
        logger.error("Could not roll back upload session; closing it before verification", exc_info=True)
        db.close()


def _discard_upload_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.error("Uncommitted CV upload file requires cleanup: %s", path, exc_info=True)


def persist_cv_upload(
    contents: bytes,
    filename: str,
    extension: str,
    file_hash: str,
    user_id: int,
    db: Session,
) -> tuple[CVResponse, str, str]:
    root = Path(settings.UPLOAD_DIR).resolve()
    path = root / f"{uuid.uuid4().hex}{extension}"
    file_path = str(path)
    run_id = uuid.uuid4().hex
    created_file = False
    commit_attempted = False
    result = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents a collision from truncating an existing CV.
        with path.open("xb") as output:
            created_file = True
            output.write(contents)
        cv = CV(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=len(contents),
            file_hash=file_hash,
            analysis_run_id=run_id,
            status="uploaded",
        )
        db.add(cv)
        db.flush()
        result = CVResponse.model_validate(cv)
        commit_attempted = True
        db.commit()
    except Exception as error:
        _rollback_upload(db)
        if commit_attempted:
            try:
                stored_id = _stored_cv_id(db, result.id, file_path)
            except Exception as verification_error:
                logger.error("Upload commit could not be verified; preserve file: %s", path, exc_info=True)
                raise HTTPException(
                    status_code=503,
                    detail="Chưa xác nhận được kết quả lưu CV. Vui lòng tải lại danh sách trước khi thử tải lên lần nữa.",
                ) from verification_error
            if stored_id is not None:
                # The server has confirmed the commit; keep the file and queue AI normally.
                return result, file_path, run_id
        if created_file:
            _discard_upload_file(path)
        if isinstance(error, OSError):
            raise HTTPException(
                status_code=503,
                detail="Không thể lưu file CV lúc này. Vui lòng thử lại sau.",
            ) from error
        raise
    return result, file_path, run_id
