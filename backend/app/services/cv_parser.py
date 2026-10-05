"""
CV Text Extraction Service
Supports: PDF (PyMuPDF), DOCX (python-docx)
"""
import os
import logging

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from PDF or DOCX file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return _extract_from_docx(file_path)
    else:
        raise ValueError(f"Định dạng file không được hỗ trợ: {ext}")


def _extract_from_pdf(file_path: str) -> str:
    """Extract text blocks, then OCR scanned PDFs when needed."""
    try:
        import fitz
        doc = fitz.open(file_path)
        try:
            pages = []
            for page in doc:
                text = page.get_text("text")
                if text:
                    pages.append(text.strip())
            extracted = "\n".join(pages).strip()
        finally:
            doc.close()
        if len(extracted) < 80:
            ocr = _extract_pdf_with_ocr(file_path)
            if len(ocr) > len(extracted):
                return ocr
        return extracted
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed")
    except Exception as exc:
        raise RuntimeError(f"PDF read error: {exc}")
def _extract_pdf_with_ocr(file_path: str) -> str:
    """OCR image-only PDFs; returns empty text if OCR is unavailable."""
    try:
        import io
        import fitz
        import pytesseract
        from PIL import Image
        from app.core.config import settings
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        doc = fitz.open(file_path)
        try:
            chunks = []
            for page in doc:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                    chunks.append(pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES))
        finally:
            doc.close()
        return "\n".join(chunks).strip()
    except Exception as exc:
        logger.exception("OCR failed for %s", file_path)
        raise RuntimeError("Không thể OCR PDF; kiểm tra Tesseract và bộ ngôn ngữ đã cài đặt") from exc


def _extract_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for section in doc.sections:
            paragraphs.extend(p.text.strip() for p in section.header.paragraphs if p.text.strip())
            paragraphs.extend(p.text.strip() for p in section.footer.paragraphs if p.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_data:
                    paragraphs.append(" | ".join(row_data))
        return "\n".join(paragraphs).strip()
    except ImportError:
        raise RuntimeError("python-docx is not installed")
    except Exception as exc:
        raise RuntimeError(f"DOCX read error: {exc}")