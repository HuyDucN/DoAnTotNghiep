import pymysql
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

conn = pymysql.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME,
    charset='utf8mb4',
)
cursor = conn.cursor()

sqls = [
    'ALTER TABLE cvs ADD COLUMN file_hash VARCHAR(64) NULL DEFAULT NULL',
    'CREATE INDEX idx_cvs_file_hash ON cvs (file_hash)',
]

for sql in sqls:
    try:
        cursor.execute(sql)
        print(f'OK: {sql[:70]}')
    except Exception as e:
        print(f'SKIP: {e}')

conn.commit()
conn.close()
print('Migration 003 (file_hash) completed!')
