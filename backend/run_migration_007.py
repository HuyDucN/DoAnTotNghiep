"""Thêm mã đối chiếu dữ liệu CV cho kết quả so khớp; có thể chạy lại."""
from pathlib import Path
import sys

import pymysql


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.core.config import settings

    connection = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER,
        password=settings.DB_PASSWORD, database=settings.DB_NAME,
        charset="utf8mb4", connect_timeout=5,
    )
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SHOW COLUMNS FROM skill_gaps WHERE Field = %s", ("cv_input_hash",))
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute("ALTER TABLE skill_gaps ADD COLUMN cv_input_hash VARCHAR(64) NULL DEFAULT NULL")
                print("Migration 007: đã thêm cột cv_input_hash.")
            elif existing["Type"].lower() != "varchar(64)" or existing["Null"] != "YES":
                raise RuntimeError("Cột cv_input_hash đã tồn tại nhưng khác cấu trúc mong đợi; cần kiểm tra schema.")
            else:
                print("Migration 007: cột cv_input_hash đã tồn tại đúng cấu trúc.")
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
