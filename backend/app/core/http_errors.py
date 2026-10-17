"""Phản hồi lỗi JSON và CORS cho cả lỗi ngoài dự kiến."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def configure_http_errors(app: FastAPI, origins: list[str]) -> CORSMiddleware:
    async def database_error(request: Request, error: SQLAlchemyError):
        logger.error("Database error at %s", request.url.path, exc_info=error)
        return JSONResponse(
            status_code=503,
            content={"detail": "Không thể truy cập dữ liệu lúc này. Vui lòng thử lại sau."},
        )

    async def unexpected_error(request: Request, error: Exception):
        logger.error("Unexpected error at %s", request.url.path, exc_info=error)
        return JSONResponse(
            status_code=500,
            content={"detail": "Máy chủ gặp lỗi khi xử lý yêu cầu. Vui lòng thử lại sau."},
        )

    app.add_exception_handler(SQLAlchemyError, database_error)
    app.add_exception_handler(Exception, unexpected_error)
    # CORS phải nằm ngoài ServerErrorMiddleware để phản hồi 500 vẫn có header.
    return CORSMiddleware(
        app,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
