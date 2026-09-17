from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    job_type = Column(
        Enum("full_time", "part_time", "internship", "freelance"),
        default="full_time",
    )
    level = Column(
        Enum("intern", "fresher", "junior", "mid", "senior", "lead"),
        default="junior",
    )
    category = Column(
        Enum("backend", "frontend", "fullstack", "data", "ai_ml", "devops", "mobile", "qa", "other"),
        default="other",
    )
    description = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    skill_gaps = relationship("SkillGap", back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    is_required = Column(Boolean, default=True)  # True=required, False=preferred
    importance = Column(
        Enum("high", "medium", "low"), default="medium"
    )

    # Relationships
    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")
