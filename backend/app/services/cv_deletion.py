"""Xóa CV với thao tác file có thể hoàn tác trước khi DB commit."""
import logging
from pathlib import Path
import stat
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cv import CV


logger = logging.getLogger(__name__)


def _stage_cv_file(file_path: str) -> Optional[tuple[Path, Path]]:
    invalid_path = HTTPException(status_code=409, detail="Đường dẫn lưu CV không hợp lệ. Vui lòng liên hệ quản trị viên.")
    try:
        if not file_path:
            raise invalid_path
        root = Path(settings.UPLOAD_DIR).resolve()
        stored_path = Path(file_path)
        original = stored_path.resolve()
        if original == root or not original.is_relative_to(root) or stored_path.is_symlink():
            raise invalid_path
        try:
            file_stat = original.stat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(file_stat.st_mode):
            raise invalid_path
        staged = original.with_name(f".{uuid.uuid4().hex}.deleting")
        try:
            original.rename(staged)
        except FileNotFoundError:
            return None
        return original, staged
    except (ValueError, RuntimeError) as error:
        raise invalid_path from error
    except OSError as error:
        raise HTTPException(status_code=503, detail="Chưa thể xử lý file CV để xóa. Vui lòng thử lại sau.") from error


def delete_stored_cv(cv_id: int, db: Session, owner_id: Optional[int] = None) -> None:
    query = db.query(CV).filter(CV.id == cv_id)
    if owner_id is not None:
        query = query.filter(CV.user_id == owner_id)
    cv = query.with_for_update().populate_existing().first()
    if cv is None:
        raise HTTPException(status_code=404, detail="CV không tồn tại")

    staged_file = _stage_cv_file(cv.file_path)
    try:
        db.delete(cv)
        db.commit()
    except Exception:
        try:
            db.rollback()
        finally:
            if staged_file is not None:
                original, staged = staged_file
                try:
                    if original.exists() or original.is_symlink():
                        raise FileExistsError("Original CV path was recreated during deletion")
                    staged.rename(original)
                except OSError as error:
                    logger.critical("Could not restore staged file for CV %s: %s", cv_id, staged, exc_info=True)
                    raise HTTPException(
                        status_code=503,
                        detail="Không thể khôi phục file CV sau lỗi lưu dữ liệu. Vui lòng liên hệ quản trị viên.",
                    ) from error
        raise

    if staged_file is not None:
        _, staged = staged_file
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            # The DB deletion already succeeded. Keep the unreferenced file and
            # record its exact path for operator cleanup instead of reporting a retryable delete.
            logger.error("CV %s deleted from database; staged file requires cleanup: %s", cv_id, staged, exc_info=True)
