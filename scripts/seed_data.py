"""Seed tối thiểu cho môi trường phát triển; chạy thủ công sau migration."""
from app.core.database import SessionLocal
# Đăng ký các model liên quan trước khi SQLAlchemy cấu hình relationship.
from app.models import cv, job, profile, skill_gap, user
from app.services.skill_catalog import get_or_create_skill

SKILLS = [("Python", "programming_language"), ("FastAPI", "framework"), ("MySQL", "database")]


def main():
    db = SessionLocal()
    try:
        for name, category in SKILLS:
            get_or_create_skill(db, name, category=category)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
