import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, cv, jobs, users, skills

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống AI phân tích CV và đánh giá khoảng cách kỹ năng",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Tăng giới hạn kích thước request lên 50MB
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 50 * 1024 * 1024):
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Giới hạn kích thước upload 50MB
app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=500 * 1024 * 1024)

# Mount static files for uploaded CVs
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
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
