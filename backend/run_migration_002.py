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
    ('jobs', 'ALTER TABLE jobs ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0'),
    ('jobs', 'ALTER TABLE jobs ADD COLUMN deleted_at DATETIME NULL DEFAULT NULL'),
    ('jobs', 'CREATE INDEX idx_jobs_is_deleted ON jobs (is_deleted)'),
    ('skills', 'ALTER TABLE skills ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0'),
    ('skills', 'ALTER TABLE skills ADD COLUMN deleted_at DATETIME NULL DEFAULT NULL'),
    ('skills', 'CREATE INDEX idx_skills_is_deleted ON skills (is_deleted)'),
]

for table, sql in sqls:
    try:
        cursor.execute(sql)
        print(f'OK: {sql[:70]}')
    except Exception as e:
        print(f'SKIP: {e}')

conn.commit()
conn.close()
print('Migration 002 (soft_delete) completed!')
