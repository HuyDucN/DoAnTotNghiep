"""Thêm mã lần phân tích CV; có thể chạy lại sau khi cột đã tồn tại."""
from pathlib import Path
import sys

import pymysql


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.core.config import settings

    connection = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
        connect_timeout=5,
    )
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SHOW COLUMNS FROM cvs WHERE Field = %s", ("analysis_run_id",))
            existing = cursor.fetchone()
            if existing:
                if existing["Type"].lower() != "varchar(32)" or existing["Null"] != "YES":
                    raise RuntimeError("Cột analysis_run_id đã tồn tại nhưng khác VARCHAR(32) NULL; cần kiểm tra schema.")
                print("Migration 005: cột analysis_run_id đã tồn tại đúng cấu trúc.")
                return
            cursor.execute("ALTER TABLE cvs ADD COLUMN analysis_run_id VARCHAR(32) NULL DEFAULT NULL")
        connection.commit()
        print("Migration 005: đã thêm cột analysis_run_id cho bảng cvs.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
