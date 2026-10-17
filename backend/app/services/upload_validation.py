"""Kiểm tra nội dung file CV thay vì chỉ dựa vào MIME trình duyệt gửi."""
import io
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

import fitz
from fastapi import HTTPException

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/x-pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def validate_cv_upload(filename: str | None, content_type: str | None, contents: bytes, max_size: int) -> str:
    if not contents:
        raise HTTPException(status_code=400, detail="File CV đang trống. Vui lòng chọn file khác.")
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail=f"File không được vượt quá {max_size // (1024 * 1024)}MB")

    mime = (content_type or "").split(";", 1)[0].strip().lower()
    extension = PurePath(filename or "").suffix.lower()
    if not extension:
        extension = SUPPORTED_MIME_TYPES.get(mime, "")
    if extension not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF hoặc DOCX. File DOC cần chuyển sang DOCX hoặc PDF.")

    if extension == ".pdf":
        try:
            with fitz.open(stream=contents, filetype="pdf") as document:
                if document.needs_pass:
                    raise HTTPException(status_code=400, detail="PDF có mật khẩu. Vui lòng xuất bản PDF không có mật khẩu trước khi tải lên.")
                if document.page_count == 0:
                    raise HTTPException(status_code=400, detail="PDF không có trang nào để phân tích.")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Không đọc được PDF. File có thể bị hỏng hoặc chỉ được đổi đuôi thành .pdf.") from exc
    else:
        try:
            with ZipFile(io.BytesIO(contents)) as archive:
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
                    raise HTTPException(status_code=400, detail="Nội dung file không phải DOCX hợp lệ.")
        except HTTPException:
            raise
        except (BadZipFile, OSError) as exc:
            raise HTTPException(status_code=400, detail="Không đọc được DOCX. Vui lòng mở và lưu lại file bằng Word.") from exc
    return extension
