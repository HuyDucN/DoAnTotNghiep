"""Tạo các Job mẫu để kiểm thử CV Match và Skill Gap.

Chạy từ thư mục gốc: python backend/seed_sample_jobs.py
Script có thể chạy nhiều lần; Job cùng title/company sẽ được bỏ qua.
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal
from app.models.job import Job, JobSkill
from app.models.skill import Skill
# Import related models so SQLAlchemy can register every relationship before
# the first query configures the Job mapper.
from app.models.cv import CV
from app.models.profile import Profile
from app.models.skill_gap import SkillGap
from app.models.user import User
from app.services.skill_names import normalize_skill_name
from app.services.skill_catalog import get_or_create_skill as resolve_skill


SAMPLE_JOBS = [
    {
        "title": "Junior Backend Developer",
        "company": "TechNova Labs",
        "location": "Hà Nội / Hybrid",
        "job_type": "full_time",
        "level": "junior",
        "category": "backend",
        "salary_min": 900,
        "salary_max": 1500,
        "description": "Phát triển API backend cho sản phẩm SaaS. Required: Python, FastAPI, SQL, Git. Preferred: Docker, Redis.",
        "required": [("Python", "high"), ("FastAPI", "high"), ("SQL", "medium"), ("Git", "medium")],
        "preferred": [("Docker", "medium"), ("Redis", "low")],
    },
    {
        "title": "Frontend React Developer",
        "company": "PixelWorks",
        "location": "Remote",
        "job_type": "full_time",
        "level": "mid",
        "category": "frontend",
        "salary_min": 1200,
        "salary_max": 2200,
        "description": "Xây dựng giao diện web hiện đại. Required: JavaScript, TypeScript, React, HTML, CSS. Preferred: Vue, Docker.",
        "required": [("JavaScript", "high"), ("TypeScript", "high"), ("React", "high"), ("HTML", "medium"), ("CSS", "medium")],
        "preferred": [("Vue", "low"), ("Docker", "low")],
    },
    {
        "title": "Data Analyst Intern",
        "company": "Insight Analytics",
        "location": "Đà Nẵng",
        "job_type": "internship",
        "level": "intern",
        "category": "data",
        "salary_min": 300,
        "salary_max": 600,
        "description": "Hỗ trợ phân tích dữ liệu và báo cáo kinh doanh. Required: SQL, Python, Excel. Preferred: Power BI, Statistics.",
        "required": [("SQL", "high"), ("Python", "medium"), ("Excel", "medium")],
        "preferred": [("Power BI", "medium"), ("Statistics", "low")],
    },
    {
        "title": "Machine Learning Engineer",
        "company": "AI Horizon",
        "location": "Hồ Chí Minh",
        "job_type": "full_time",
        "level": "senior",
        "category": "ai_ml",
        "salary_min": 2200,
        "salary_max": 4000,
        "description": "Phát triển và triển khai mô hình AI. Required: Python, Machine Learning, TensorFlow, SQL. Preferred: PyTorch, Docker, AWS.",
        "required": [("Python", "high"), ("Machine Learning", "high"), ("TensorFlow", "high"), ("SQL", "medium")],
        "preferred": [("PyTorch", "medium"), ("Docker", "medium"), ("AWS", "low")],
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudBridge",
        "location": "Remote / Việt Nam",
        "job_type": "full_time",
        "level": "mid",
        "category": "devops",
        "salary_min": 1800,
        "salary_max": 3200,
        "description": "Quản lý hạ tầng cloud và pipeline CI/CD. Required: Linux, Docker, Kubernetes, AWS, Git. Preferred: Terraform, Python.",
        "required": [("Linux", "high"), ("Docker", "high"), ("Kubernetes", "high"), ("AWS", "medium"), ("Git", "medium")],
        "preferred": [("Terraform", "medium"), ("Python", "low")],
    },
]


def normalize(name: str) -> str:
    return normalize_skill_name(name)


def get_or_create_skill(db, name: str) -> Skill:
    return resolve_skill(db, name)


def seed() -> None:
    db = SessionLocal()
    created = 0
    skipped = 0
    try:
        for item in SAMPLE_JOBS:
            existing = db.query(Job).filter(
                Job.title == item["title"],
                Job.company == item["company"],
            ).first()
            if existing and not existing.is_deleted:
                skipped += 1
                continue

            job = existing or Job()
            job.title = item["title"]
            job.company = item["company"]
            job.location = item["location"]
            job.job_type = item["job_type"]
            job.level = item["level"]
            job.category = item["category"]
            job.salary_min = item["salary_min"]
            job.salary_max = item["salary_max"]
            job.description = item["description"]
            job.is_active = True
            job.is_deleted = False
            job.deleted_at = None
            if existing:
                db.query(JobSkill).filter(JobSkill.job_id == job.id).delete(synchronize_session=False)
            else:
                db.add(job)
                db.flush()

            for name, importance in item["required"]:
                db.add(JobSkill(job_id=job.id, skill_id=get_or_create_skill(db, name).id, is_required=True, importance=importance))
            for name, importance in item["preferred"]:
                db.add(JobSkill(job_id=job.id, skill_id=get_or_create_skill(db, name).id, is_required=False, importance=importance))
            created += 1

        db.commit()
        print(f"Đã tạo/khôi phục {created} Job mẫu; bỏ qua {skipped} Job đã tồn tại.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
