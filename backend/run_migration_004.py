import os
import sys

import pymysql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings


connection = pymysql.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME,
    charset="utf8mb4",
)

try:
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('user', 'admin', 'employer') NOT NULL DEFAULT 'user'"
        )
    connection.commit()
    print("Migration 004 (employer role) completed!")
finally:
    connection.close()
