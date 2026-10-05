"""Seed tối thiểu cho môi trường phát triển; chạy thủ công sau migration."""
from app.core.database import SessionLocal
from app.models.skill import Skill

SKILLS = [("Python", "programming_language"), ("FastAPI", "framework"), ("MySQL", "database")]


def main():
    db = SessionLocal()
    try:
        for name, category in SKILLS:
            normalized = name.lower().replace(" ", "_")
            if not db.query(Skill).filter(Skill.normalized_name == normalized).first():
                db.add(Skill(name=name, normalized_name=normalized, category=category))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
