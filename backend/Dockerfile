FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tesseract + fonts cho OCR (pytesseract, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    fonts-dejavu \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install -r requirements.txt

COPY backend ./backend
COPY pytest.ini ./pytest.ini
COPY tests ./tests

WORKDIR /app/backend

EXPOSE 8000

# Migrate rồi mới chạy app — tránh lỗi thiếu cột (vd users.is_verified) khi deploy bản mới.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
