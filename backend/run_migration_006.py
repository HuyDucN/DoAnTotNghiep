"""Thêm thông tin công việc và thời gian so khớp; có thể chạy lại."""
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
    definitions = {
        "job_snapshot": ("json", "ALTER TABLE skill_gaps ADD COLUMN job_snapshot JSON NULL DEFAULT NULL"),
        "matched_at": ("datetime(6)", "ALTER TABLE skill_gaps ADD COLUMN matched_at DATETIME(6) NULL DEFAULT NULL"),
    }
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            missing = []
            for column, (expected_type, sql) in definitions.items():
                cursor.execute("SHOW COLUMNS FROM skill_gaps WHERE Field = %s", (column,))
                existing = cursor.fetchone()
                if existing is None:
                    missing.append((column, sql))
                elif existing["Type"].lower() != expected_type or existing["Null"] != "YES":
                    raise RuntimeError(f"Cột {column} đã tồn tại nhưng khác cấu trúc mong đợi; cần kiểm tra schema.")
            for column, sql in missing:
                cursor.execute(sql)
                print(f"Migration 006: đã thêm cột {column}.")
        connection.commit()
        if not missing:
            print("Migration 006: các cột đã tồn tại đúng cấu trúc.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
