import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from app.core.http_errors import configure_http_errors
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api import admin, auth, cv, jobs, users, skills

# Keep development convenience without silently mutating production schemas.
if settings.ENVIRONMENT.lower() in {"development", "dev"}:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống AI phân tích CV và đánh giá khoảng cách kỹ năng",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request includes multipart metadata, so leave a small overhead margin; the
# upload endpoint enforces the actual 10MB file limit.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 11 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_upload_size:
                return Response(
                    content=f"File quá lớn. Giới hạn tối đa là {self.max_upload_size // (1024*1024)}MB",
                    status_code=413,
                )
        return await call_next(request)

# Allow multipart overhead; cv.py enforces the 10MB file-size limit.
app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=11 * 1024 * 1024)

# Mount static files for uploaded CVs
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def recover_stale_cv_analysis(stale_minutes: int = 30) -> int:
    """Dua CV ket o uploaded/processing qua lau ve uploaded de reanalyze thu lai.

    Giu nguyen analysis_run_id hien tai; worker chi nhan viec khi ma con khop
    nen khong ghi de lan phan tich moi hon.
    """
    from app.models.cv import CV
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    db = SessionLocal()
    try:
        stale = (
            db.query(CV)
            .filter(CV.status.in_(["uploaded", "processing"]))
            .all()
        )
        count = 0
        for cv in stale:
            last = cv.updated_at or cv.created_at
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last is not None and last >= cutoff:
                continue
            cv.status = "uploaded"
            count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


@app.on_event("startup")
def _recover_stale_analysis_on_startup():
    if settings.ENVIRONMENT.lower() in {"development", "dev", "test"}:
        return
    try:
        recovered = recover_stale_cv_analysis()
        if recovered:
            print(f"[Startup] Dua {recovered} CV ket ve uploaded de thu lai.")
    except Exception as exc:
        print(f"[Startup] Bo qua phuc hoi CV ket: {exc}")
    try:
        from app.services.analysis_queue import start_analysis_worker
        start_analysis_worker()
    except Exception as exc:
        print(f"[Startup] Khong khoi dong duoc analysis worker: {exc}")


# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(cv.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")

@app.get("/", tags=["Health"])
def root():
    return {
        "message": f"🚀 {settings.APP_NAME} API is running",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app = configure_http_errors(app, settings.cors_origins_list)
